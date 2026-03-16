from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import Color
from google import genai
from datetime import timedelta, datetime
import json
import logging
import tempfile
import os
import base64
import io
import hashlib
import pytz
import requests
import threading
import re

from dotenv import load_dotenv
import random
from django.db import close_old_connections

from .models import Interview, InterviewResponse, InterviewFrames, VoiceInterviewSession, Question
from utils.hdfs_client import HDFSClient

HTTP_SESSION = requests.Session()
TTS_CACHE_DIR = os.path.join(settings.MEDIA_ROOT, 'tts_cache')
LOCAL_AUDIO_RESPONSES_DIR = os.path.join(settings.MEDIA_ROOT, 'audio_responses')
SERVER_TTS_ENABLED = getattr(settings, 'VOICE_INTERVIEW_TTS_ENABLED', False)
INTERVIEW_ANALYSIS_MODEL = settings.OPENROUTER_CONFIG.get('MODEL', 'deepseek/deepseek-r1-0528')


def get_random_question(interview, excluded_question_ids=None):
    """
    Fetch a random question from Question model
    excluding already asked questions.
    """
    # Get already asked question IDs
    asked_ids = set(interview.responses.values_list('question__id', flat=True))
    if excluded_question_ids:
        asked_ids.update(excluded_question_ids)

    # Exclude already asked
    available_questions = Question.objects.exclude(id__in=asked_ids)

    if not available_questions.exists():
        return None

    return random.choice(available_questions)


def _ensure_directory(path):
    os.makedirs(path, exist_ok=True)


def _save_audio_locally(interview, question_number, audio_bytes):
    _ensure_directory(LOCAL_AUDIO_RESPONSES_DIR)
    interview_dir = os.path.join(LOCAL_AUDIO_RESPONSES_DIR, f"interview_{interview.id}")
    _ensure_directory(interview_dir)
    filename = f"question_{question_number}_{timezone.now().strftime('%Y%m%d_%H%M%S_%f')}.webm"
    local_path = os.path.join(interview_dir, filename)

    with open(local_path, 'wb') as audio_file:
        audio_file.write(audio_bytes)

    return local_path


def _upload_audio_to_hdfs_in_background(response_id, interview_id, question_number, local_audio_path):
    close_old_connections()
    try:
        response_record = InterviewResponse.objects.select_related('interview').get(id=response_id)
        hdfs_client = HDFSClient()
        if not hdfs_client.is_connected():
            logger.warning("Skipping HDFS upload because HDFS is unavailable")
            return

        with open(local_audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()

        hdfs_audio_path = (
            f"/student_audio_responses/"
            f"interview_{interview_id}/"
            f"question_{question_number}.webm"
        )

        if hdfs_client.write_file(hdfs_audio_path, audio_bytes):
            response_record.audio_file_path = hdfs_audio_path
            response_record.save(update_fields=['audio_file_path'])
            logger.info(f"Background HDFS upload completed for response {response_id}")
    except Exception as exc:
        logger.error(f"Background HDFS upload failed for response {response_id}: {exc}")
    finally:
        close_old_connections()


def _build_question_audio_payload(agent, question_text):
    if not SERVER_TTS_ENABLED:
        return {
            'has_audio': False,
            'audio_base64': None,
        }

    audio_base64 = agent.text_to_speech_gtts(question_text)
    return {
        'has_audio': audio_base64 is not None,
        'audio_base64': audio_base64,
    }


def _append_interview_context(voice_session, question_obj, transcription):
    context_entries = voice_session.interview_context if isinstance(voice_session.interview_context, list) else []
    context_entries.append({
        'question_number': voice_session.current_question_number,
        'question_id': str(question_obj.id),
        'ai_question': question_obj.question_text,
        'response': transcription,
        'timestamp': timezone.now().isoformat(),
        'audio_file_saved': True,
    })
    voice_session.interview_context = context_entries
    voice_session.save(update_fields=['interview_context', 'updated_at'])


def _build_interview_analysis_prompt(interview, context_entries):
    response_blocks = []
    for entry in context_entries:
        response_blocks.append(
            f"Question {entry.get('question_number')}:\n"
            f"Prompt: {entry.get('ai_question', '')}\n"
            f"Candidate answer: {entry.get('response', '')}\n"
        )

    compiled_responses = "\n".join(response_blocks)
    return f"""
You are evaluating a completed mock technical interview for a data science / machine learning candidate.

Interview metadata:
- Interview ID: {interview.id}
- Total questions answered: {len(context_entries)}

Evaluate the candidate only from the question/answer transcript below.
Return a strict JSON object with scores from 0 to 100 and concise bullet-style feedback.

Transcript:
{compiled_responses}

Required JSON format:
{{
  "technical_score": <0-100 number>,
  "communication_score": <0-100 number>,
  "confidence_score": <0-100 number>,
  "overall_score": <0-100 number>,
  "strengths": ["short point", "short point"],
  "improvements": ["short point", "short point"],
  "summary": "2-4 sentence summary"
}}
"""


def _fallback_interview_scores(context_entries):
    answered = [entry for entry in context_entries if entry.get('response')]
    avg_length = sum(len(entry.get('response', '').split()) for entry in answered) / max(len(answered), 1)
    technical_score = min(85.0, max(35.0, 35.0 + avg_length * 2.2))
    communication_score = min(90.0, max(40.0, 40.0 + avg_length * 1.8))
    confidence_score = min(88.0, max(38.0, 38.0 + avg_length * 1.6))
    overall_score = round((technical_score * 0.5) + (communication_score * 0.3) + (confidence_score * 0.2), 1)
    return {
        'technical_score': round(technical_score, 1),
        'communication_score': round(communication_score, 1),
        'confidence_score': round(confidence_score, 1),
        'overall_score': overall_score,
        'strengths': ['Completed the interview flow', 'Provided spoken responses for evaluation'],
        'improvements': ['Add more technical depth', 'Use more structured explanations'],
        'summary': 'Fallback scoring was used because automated analysis was unavailable.',
    }


def _parse_interview_analysis(response_text, context_entries):
    try:
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return _fallback_interview_scores(context_entries)

        parsed = json.loads(json_match.group())
        required_fields = ['technical_score', 'communication_score', 'confidence_score', 'overall_score']
        for field in required_fields:
            parsed[field] = max(0.0, min(100.0, float(parsed[field])))

        parsed['strengths'] = parsed.get('strengths') or []
        parsed['improvements'] = parsed.get('improvements') or []
        parsed['summary'] = parsed.get('summary') or ''
        return parsed
    except Exception as exc:
        logger.error(f"Failed to parse interview analysis response: {exc}")
        return _fallback_interview_scores(context_entries)


def _run_final_interview_analysis(interview_id):
    close_old_connections()
    try:
        interview = Interview.objects.get(id=interview_id)
        voice_session = VoiceInterviewSession.objects.filter(interview=interview).first()
        context_entries = voice_session.interview_context if voice_session and isinstance(voice_session.interview_context, list) else []

        if not context_entries:
            logger.warning(f"Skipping interview analysis for {interview_id}: no interview context available")
            interview.processing_status = 'failed'
            interview.processing_error = 'No interview context available for analysis'
            interview.save(update_fields=['processing_status', 'processing_error'])
            return

        interview.processing_status = 'processing'
        interview.processing_started_at = timezone.now()
        interview.processing_error = ''
        interview.save(update_fields=['processing_status', 'processing_started_at', 'processing_error'])

        scores = None
        api_key = settings.OPENROUTER_CONFIG.get('API_KEY')
        if api_key:
            prompt = _build_interview_analysis_prompt(interview, context_entries)
            response = HTTP_SESSION.post(
                f"{settings.OPENROUTER_CONFIG['BASE_URL']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": INTERVIEW_ANALYSIS_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1200,
                    "temperature": 0.2,
                },
                timeout=60,
            )
            if response.ok:
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
                scores = _parse_interview_analysis(content, context_entries)
            else:
                logger.error(f"Interview analysis API failed: {response.status_code} - {response.text}")

        if scores is None:
            scores = _fallback_interview_scores(context_entries)

        interview.technical_score = scores['technical_score']
        interview.communication_score = scores['communication_score']
        interview.confidence_score = scores['confidence_score']
        interview.overall_score = scores['overall_score']
        interview.analysis_completed = True
        interview.processing_status = 'analysis_complete'
        interview.processing_completed_at = timezone.now()
        interview.save(update_fields=[
            'technical_score',
            'communication_score',
            'confidence_score',
            'overall_score',
            'analysis_completed',
            'processing_status',
            'processing_completed_at',
        ])

        if voice_session:
            session_data = voice_session.session_data or {}
            session_data['analysis_summary'] = {
                'strengths': scores.get('strengths', []),
                'improvements': scores.get('improvements', []),
                'summary': scores.get('summary', ''),
                'scored_at': timezone.now().isoformat(),
            }
            voice_session.session_data = session_data
            voice_session.save(update_fields=['session_data', 'updated_at'])

        logger.info(f"Interview {interview_id} analyzed successfully with overall score {scores['overall_score']}")
    except Exception as exc:
        logger.error(f"Final interview analysis failed for {interview_id}: {exc}", exc_info=True)
        try:
            interview = Interview.objects.get(id=interview_id)
            interview.processing_status = 'failed'
            interview.processing_error = str(exc)
            interview.save(update_fields=['processing_status', 'processing_error'])
        except Exception:
            logger.error(f"Could not persist failure state for interview {interview_id}")
    finally:
        close_old_connections()
# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

User = get_user_model()

VOICE_INTERVIEW_CONFIG = {
    'OPENROUTER_API_KEY': os.getenv('OPENROUTER_API_KEY'),
    'DEEPSEEK_MODEL': 'mistralai/mistral-7b-instruct',
    'DEEPSEEK_BASE_URL': 'https://openrouter.ai/api/v1',
    'MAX_QUESTIONS': 15,
    'CONTEXT_WINDOW_SIZE': 1,
    'QUESTION_STAGES': {
        'intro': (1, 3),
        'projects': (4, 6),
        'python': (7, 9),
        'statistics': (10, 12),
        'ml': (13, 14),
        'closing': (15, 15)
    }
}


logger = logging.getLogger(__name__)
User = get_user_model()

# Try to import Kafka client, but don't fail if it's not available yet
try:
    from utils.kafka_client import KafkaFrameClient
    KAFKA_AVAILABLE = True
    logger.info("✅ Kafka client loaded successfully")
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("⚠️ Kafka client not available, using HDFS only")

#Time zone related functions
def get_ist_now():
    """Get current time in IST"""
    ist = pytz.timezone('Asia/Kolkata')
    return timezone.now().astimezone(ist)

def parse_datetime_to_ist(datetime_str):
    """Parse datetime string and ensure it's in IST"""
    from django.utils.dateparse import parse_datetime
    dt = parse_datetime(datetime_str)
    if dt:
        ist = pytz.timezone('Asia/Kolkata')
        if timezone.is_naive(dt):
            dt = ist.localize(dt)
        else:
            dt = dt.astimezone(ist)
    return dt

def format_ist_time(dt):
    """Format datetime in IST"""
    if dt:
        ist = pytz.timezone('Asia/Kolkata')
        ist_time = dt.astimezone(ist)
        return ist_time.strftime('%d %b %Y, %I:%M %p IST')
    return 'Not Set'


@login_required
def interview_interface(request):
    """Main interview interface"""
    try:
        # Get active interview for the user
        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            messages.error(request, 'No active interview found. Please start an approved interview first.')
            return redirect('student_dashboard')

        return render(request, 'interview_system/interview.html', {
            'interview': interview
        })

    except Exception as e:
        logger.error(f"Error in interview interface: {e}")
        messages.error(request, 'Error loading interview interface')
        return redirect('student_dashboard')


@staff_member_required
@require_http_methods(["GET"])
def debug_audio_hdfs_write(request):
    """Debug audio file writing to HDFS"""
    try:
        hdfs_client = HDFSClient()
        
        if not hdfs_client.is_connected():
            return JsonResponse({'error': 'HDFS not connected'}, status=500)
        
        # Create test audio data (simulating a small audio file)
        test_audio_data = b'\x00\x01\x02\x03' * 1000  # 4KB of test data
        test_path = "/student_audio_responses/test_user_STU001_attempt_1/test_audio.webm"
        
        result = hdfs_client.write_file(test_path, test_audio_data)
        
        # Try to read it back
        verification = None
        if result:
            try:
                with hdfs_client.client.read(test_path) as reader:
                    read_data = reader.read()
                    verification = {
                        'read_success': True,
                        'bytes_read': len(read_data),
                        'data_matches': read_data == test_audio_data
                    }
                # Clean up
                hdfs_client.client.delete(test_path)
            except Exception as read_error:
                verification = {
                    'read_success': False,
                    'error': str(read_error)
                }
        
        return JsonResponse({
            'write_success': result,
            'test_path': test_path,
            'test_data_size': len(test_audio_data),
            'verification': verification
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'error_type': type(e).__name__
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def debug_hdfs_write(request):
    """Debug HDFS write operations in detail"""
    try:
        hdfs_client = HDFSClient()
        
        if not hdfs_client.is_connected():
            return JsonResponse({'error': 'HDFS not connected'}, status=500)
        
        results = []
        
        # Test 1: Write to root directory
        try:
            test_path_1 = "/test_root_write.txt"
            test_data_1 = "Hello HDFS from root"
            result_1 = hdfs_client.write_file(test_path_1, test_data_1)
            results.append({
                'test': 'Write to root directory',
                'path': test_path_1,
                'success': result_1,
                'data_size': len(test_data_1)
            })
            
            # Clean up
            if result_1:
                hdfs_client.client.delete(test_path_1)
                
        except Exception as e:
            results.append({
                'test': 'Write to root directory',
                'success': False,
                'error': str(e)
            })
        
        # Test 2: Write to existing directory
        try:
            test_path_2 = "/student_audio_responses/test_write.txt"
            test_data_2 = "Hello HDFS from existing dir"
            result_2 = hdfs_client.write_file(test_path_2, test_data_2)
            results.append({
                'test': 'Write to existing directory',
                'path': test_path_2,
                'success': result_2,
                'data_size': len(test_data_2)
            })
            
            # Clean up
            if result_2:
                hdfs_client.client.delete(test_path_2)
                
        except Exception as e:
            results.append({
                'test': 'Write to existing directory',
                'success': False,
                'error': str(e)
            })
            
        # Test 3: Write JSON data
        try:
            test_path_3 = "/test_json_write.json"
            test_data_3 = '{"test": "json data", "number": 123, "array": [1,2,3]}'
            result_3 = hdfs_client.write_file(test_path_3, test_data_3)
            results.append({
                'test': 'Write JSON data',
                'path': test_path_3,
                'success': result_3,
                'data_size': len(test_data_3)
            })
            
            # Clean up
            if result_3:
                hdfs_client.client.delete(test_path_3)
                
        except Exception as e:
            results.append({
                'test': 'Write JSON data',
                'success': False,
                'error': str(e)
            })
        
        return JsonResponse({
            'hdfs_connected': True,
            'write_tests': results
        }, json_dumps_params={'indent': 2})
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'hdfs_connected': False
        }, status=500)


@staff_member_required
@require_http_methods(["GET"])
def test_hdfs_connection(request):
    """Test HDFS connection and operations"""
    try:
        hdfs_client = HDFSClient()
        
        test_results = {
            'hdfs_connected': hdfs_client.is_connected(),
            'tests': []
        }
        
        if hdfs_client.is_connected():
            # Test 1: List root directory
            try:
                root_files = hdfs_client.client.list('/')
                test_results['tests'].append({
                    'test': 'List root directory',
                    'success': True,
                    'result': root_files
                })
            except Exception as e:
                test_results['tests'].append({
                    'test': 'List root directory',
                    'success': False,
                    'error': str(e)
                })
            
            # Test 2: Create test directory
            try:
                test_dir = '/test_interview_system'
                hdfs_client.client.makedirs(test_dir, permission=755)
                test_results['tests'].append({
                    'test': 'Create test directory',
                    'success': True,
                    'result': f'Created {test_dir}'
                })
                
                # Test 3: Write test file - IMPROVED
                try:
                    test_file = f'{test_dir}/test.json'
                    test_data = '{"test": "data", "timestamp": "' + timezone.now().isoformat() + '"}'
                    
                    # Try the write_file method
                    write_success = hdfs_client.write_file(test_file, test_data)
                    
                    if write_success:
                        # Verify file exists
                        try:
                            file_list = hdfs_client.client.list(test_dir)
                            file_exists = 'test.json' in file_list
                            
                            test_results['tests'].append({
                                'test': 'Write test file',
                                'success': file_exists,
                                'result': f'File written and verified: {file_exists}',
                                'file_list': file_list
                            })
                        except Exception as verify_error:
                            test_results['tests'].append({
                                'test': 'Write test file',
                                'success': False,
                                'result': 'File written but verification failed',
                                'error': str(verify_error)
                            })
                    else:
                        test_results['tests'].append({
                            'test': 'Write test file',
                            'success': False,
                            'result': 'write_file method returned False',
                            'error': 'Check HDFS logs for details'
                        })
                        
                except Exception as write_error:
                    test_results['tests'].append({
                        'test': 'Write test file',
                        'success': False,
                        'error': str(write_error)
                    })
                
                # Clean up
                try:
                    hdfs_client.client.delete(test_dir, recursive=True)
                    test_results['cleanup'] = 'Test directory deleted successfully'
                except Exception as cleanup_error:
                    test_results['cleanup_error'] = str(cleanup_error)
                    
            except Exception as e:
                test_results['tests'].append({
                    'test': 'Create test directory',
                    'success': False,
                    'error': str(e)
                })
        
        return JsonResponse(test_results, json_dumps_params={'indent': 2})
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'hdfs_connected': False
        }, status=500)

@login_required
@require_http_methods(["POST"])
def start_interview(request, interview_id):
    """Start interview with FLEXIBLE IST time validation and separate session IDs"""

    # COMPREHENSIVE DEBUGGING
    logger.info(f"🚀 START_INTERVIEW called for interview_id: {interview_id}")
    logger.info(f"   User: {request.user.id} ({request.user.username})")
    logger.info(f"   Method: {request.method}")
    logger.info(f"   Headers: {dict(request.headers)}")
    logger.info(f"   Body: {request.body}")

    try:
        # Check if interview exists first
        try:
            interview = Interview.objects.get(id=interview_id, student=request.user)
            logger.info(f"✅ Interview found: {interview.id}")
            logger.info(f"   Status: {interview.status}")
            logger.info(f"   Scheduled: {interview.scheduled_at}")
            logger.info(f"   Expires: {interview.expires_at}")
            logger.info(f"   Created: {interview.created_at}")
            logger.info(f"   Student: {interview.student.username}")
        except Interview.DoesNotExist:
            logger.error(f"❌ Interview {interview_id} not found for user {request.user.id}")
            return JsonResponse({
                'success': False,
                'error': f'Interview {interview_id} not found for user {request.user.username}'
            }, status=404)

        # Check status
        if interview.status != 'approved':
            logger.error(f"❌ Interview {interview_id} status is '{interview.status}', not 'approved'")
            return JsonResponse({
                'success': False,
                'error': f'Interview status is "{interview.status}", not approved. Current status: {interview.status}'
            }, status=400)

        # Check if scheduled_at exists
        if not interview.scheduled_at:
            logger.error(f"❌ Interview {interview_id} has no scheduled_at time")
            return JsonResponse({
                'success': False,
                'error': 'Interview has no scheduled time set. Please contact admin.'
            }, status=400)

        # FLEXIBLE IST time validation with 15-minute grace period
        now_ist = get_ist_now()
        scheduled_ist = interview.scheduled_at.astimezone(pytz.timezone('Asia/Kolkata'))
        expires_ist = interview.expires_at.astimezone(pytz.timezone('Asia/Kolkata')) if interview.expires_at else None

        # Enhanced debugging logs
        logger.info(f"⏰ TIME VALIDATION:")
        logger.info(f"   Current IST: {now_ist}")
        logger.info(f"   Scheduled IST: {scheduled_ist}")
        logger.info(f"   Expires IST: {expires_ist}")

        time_diff_seconds = (scheduled_ist - now_ist).total_seconds()
        logger.info(f"   Time difference: {time_diff_seconds} seconds ({time_diff_seconds/60:.1f} minutes)")
        logger.info(f"   Is before scheduled? {now_ist < scheduled_ist}")

        if expires_ist:
            expires_diff_seconds = (expires_ist - now_ist).total_seconds()
            logger.info(f"   Time until expiry: {expires_diff_seconds} seconds ({expires_diff_seconds/60:.1f} minutes)")
            logger.info(f"   Is after expiry? {now_ist > expires_ist}")

        print(f"Current IST: {now_ist}")
        print(f"Scheduled IST: {scheduled_ist}")
        print(f"Expires IST: {expires_ist}")

        # IMPROVED: Allow starting 15 minutes early (grace period)
        grace_period_minutes = 15
        grace_start_time = scheduled_ist - timedelta(minutes=grace_period_minutes)

        logger.info(f"   Grace period: {grace_period_minutes} minutes")
        logger.info(f"   Grace start time: {grace_start_time}")
        logger.info(f"   Is before grace period? {now_ist < grace_start_time}")

        # Check if too early (before grace period)
        if now_ist < grace_start_time:
            minutes_until = int((grace_start_time - now_ist).total_seconds() / 60)
            logger.error(f"❌ TOO EARLY: {minutes_until} minutes until grace period starts")
            return JsonResponse({
                'success': False,
                'error': f'Interview opens at {format_ist_time(grace_start_time)} IST (15 min before scheduled time). Please wait {minutes_until} minutes.',
                'scheduled_at_ist': format_ist_time(scheduled_ist),
                'grace_start_at_ist': format_ist_time(grace_start_time),
                'minutes_until_start': minutes_until,
                'debug_info': {
                    'current_ist': format_ist_time(now_ist),
                    'scheduled_ist': format_ist_time(scheduled_ist),
                    'grace_start_ist': format_ist_time(grace_start_time),
                    'time_difference_minutes': time_diff_seconds/60,
                    'grace_period_minutes': grace_period_minutes,
                    'interview_status': interview.status
                }
            }, status=400)

        # Check if expired
        if expires_ist and now_ist > expires_ist:
            logger.error(f"❌ EXPIRED: Interview expired at {expires_ist}")
            interview.status = 'expired'
            interview.save()
            return JsonResponse({
                'success': False,
                'error': f'Interview expired at {format_ist_time(expires_ist)}',
                'expired_at_ist': format_ist_time(expires_ist),
                'debug_info': {
                    'current_ist': format_ist_time(now_ist),
                    'expired_at_ist': format_ist_time(expires_ist)
                }
            }, status=400)

        # SUCCESS: Within valid time window
        if now_ist < scheduled_ist:
            minutes_early = int((scheduled_ist - now_ist).total_seconds() / 60)
            logger.info(f"✅ Early start allowed - {minutes_early} minutes before scheduled time")
        else:
            minutes_late = int((now_ist - scheduled_ist).total_seconds() / 60)
            logger.info(f"✅ On-time or late start - {minutes_late} minutes after scheduled time")

        # Start the interview
        logger.info(f"🎯 Starting interview - updating status to 'in_progress'")
        interview.status = 'in_progress'
        interview.started_at = timezone.now()
        interview.save()
        logger.info(f"✅ Interview status updated and saved")

        # Initialize both frame and video session IDs
                # Initialize session IDs safely
        frame_session_id = None
        video_session_id = None

        logger.info(f"🔗 Initializing Kafka sessions - KAFKA_AVAILABLE: {KAFKA_AVAILABLE}")

        if KAFKA_AVAILABLE:
            try:
                logger.info("🔗 Creating KafkaFrameClient...")
                kafka_client = KafkaFrameClient()

                if kafka_client.is_connected():
                    logger.info("✅ Kafka client connected, creating sessions...")

                    # Create frame session
                    frame_session_id = kafka_client.start_frame_session(
                        user=request.user,
                        interview=interview,
                        total_frames_estimate=0
                    )
                    logger.info(f"✅ Frame session created: {frame_session_id}")

                    # Create video session
                    video_session_id = (
                        f"video_session_{interview.id}_{request.user.id}_"
                        f"{int(timezone.now().timestamp())}"
                    )
                    logger.info(f"✅ Video session created: {video_session_id}")
                else:
                    logger.warning("⚠️ Kafka client not connected")

                kafka_client.close()

            except Exception as e:
                logger.error(f"❌ Failed to start Kafka sessions: {e}", exc_info=True)

        # Create or update InterviewFrames record
        logger.info("💾 Creating/updating InterviewFrames record...")

        try:
            frames_record, created = InterviewFrames.objects.get_or_create(
                interview=interview,
                defaults={
                    'kafka_session_id': frame_session_id,
                    'video_session_id': video_session_id,
                    'storage_method': 'kafka' if frame_session_id else 'local',
                    'total_frames': 0,
                    'total_video_chunks': 0,
                    'video_recording_started_at': timezone.now() if video_session_id else None
                }
            )

            if not created:
                frames_record.kafka_session_id = frame_session_id
                frames_record.video_session_id = video_session_id

                if frame_session_id:
                    frames_record.storage_method = 'kafka'

                if video_session_id and not frames_record.video_recording_started_at:
                    frames_record.video_recording_started_at = timezone.now()

                frames_record.save()

            logger.info(
                f"✅ Frames record {'created' if created else 'updated'} "
                f"for interview {interview.id}"
            )
            logger.info(f"   Frame session: {frame_session_id}")
            logger.info(f"   Video session: {video_session_id}")

        except Exception as e:
            logger.error(f"❌ Failed to create/update InterviewFrames: {e}", exc_info=True)

        # Prepare success message
        success_message = f'Interview started successfully at {format_ist_time(now_ist)}'

        if now_ist < scheduled_ist:
            minutes_early = int((scheduled_ist - now_ist).total_seconds() / 60)
            success_message += f' ({minutes_early} minutes before scheduled time)'
        else:
            minutes_after = int((now_ist - scheduled_ist).total_seconds() / 60)
            if minutes_after > 0:
                success_message += f' ({minutes_after} minutes after scheduled time)'

        logger.info(f"✅ Interview {interview.id} started successfully")
        logger.info(f"   Message: {success_message}")

        response_data = {
            'success': True,
            'message': success_message,
            'interview_id': interview.id,
            'frame_session_id': frame_session_id,
            'video_session_id': video_session_id,
            'started_at_ist': format_ist_time(now_ist),
            'scheduled_at_ist': format_ist_time(scheduled_ist),
            'expires_at_ist': format_ist_time(expires_ist) if expires_ist else None,
            'early_start': now_ist < scheduled_ist,
            'redirect_url': '/interview/',
            'debug_info': {
                'kafka_available': KAFKA_AVAILABLE,
                'frame_session_created': frame_session_id is not None,
                'video_session_created': video_session_id is not None,
                'time_difference_minutes': time_diff_seconds / 60,
                'grace_period_used': now_ist < scheduled_ist
            }
        }

        logger.info("📤 Sending success response")
        return JsonResponse(response_data)

        # Prepare success message
        success_message = f'Interview started successfully at {format_ist_time(now_ist)}'
        if now_ist < scheduled_ist:
            minutes_early = int((scheduled_ist - now_ist).total_seconds() / 60)
            success_message += f' ({minutes_early} minutes before scheduled time)'
        else:
            minutes_after = int((now_ist - scheduled_ist).total_seconds() / 60)
            if minutes_after > 0:
                success_message += f' ({minutes_after} minutes after scheduled time)'

        logger.info(f"✅ Interview {interview_id} started successfully")
        logger.info(f"   Message: {success_message}")

        response_data = {
            'success': True,
            'message': success_message,
            'interview_id': interview.id,
            'frame_session_id': frame_session_id,
            'video_session_id': video_session_id,
            'started_at_ist': format_ist_time(now_ist),
            'scheduled_at_ist': format_ist_time(scheduled_ist),
            'expires_at_ist': format_ist_time(expires_ist) if expires_ist else None,
            'early_start': now_ist < scheduled_ist,
            'redirect_url': '/interview/',
            'debug_info': {
                'kafka_available': KAFKA_AVAILABLE,
                'frame_session_created': frame_session_id is not None,
                'video_session_created': video_session_id is not None,
                'time_difference_minutes': time_diff_seconds/60,
                'grace_period_used': now_ist < scheduled_ist
            }
        }

        logger.info(f"📤 Sending success response: {response_data}")
        return JsonResponse(response_data)

    except Interview.DoesNotExist:
        logger.error(f"❌ Interview {interview_id} not found for user {request.user.id}")
        return JsonResponse({
            'success': False,
            'error': f'Interview not found for user {request.user.username}'
        }, status=404)
    except Exception as e:
        logger.error(f"❌ UNEXPECTED EXCEPTION in start_interview: {type(e).__name__}: {str(e)}")
        logger.error(f"   Interview ID: {interview_id}")
        logger.error(f"   User: {request.user.id} ({request.user.username})")
        logger.error(f"   Full traceback: ", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Internal server error starting interview. Please contact support.',
            'debug_error': str(e),
            'debug_info': {
                'interview_id': interview_id,
                'user_id': request.user.id,
                'username': request.user.username,
                'exception_type': type(e).__name__
            }
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def stream_frame(request):
    """Stream a single frame to Kafka in real-time"""
    try:
        print("🔥 STREAM_FRAME VIEW HIT")

        if not request.user.is_authenticated:
            print("❌ User not authenticated")
            return JsonResponse({'error': 'Authentication required'}, status=401)

        interview = Interview.objects.filter(
            student=request.user
        ).order_by('-id').first()

        if not interview:
            print("❌ No interview found")
            return JsonResponse({'success': False, 'message': 'No interview found'})

        try:
            data = json.loads(request.body)
        except Exception:
            print("❌ Invalid JSON received")
            return JsonResponse({'success': False, 'message': 'Invalid JSON'})

        frame_data = data.get('frame_data')
        frame_number = data.get('frame_number', 0)
        width = data.get('width', 0)
        height = data.get('height', 0)

        if not frame_data:
            print("❌ No frame data provided")
            return JsonResponse({'success': False, 'message': 'No frame data provided'})

        print(f"✅ Frame received | Frame #{frame_number}")

        frames_record = InterviewFrames.objects.filter(
            interview=interview
        ).first()

        if not frames_record or not frames_record.kafka_session_id:
            print("❌ Kafka session not ready")
            return JsonResponse({'success': False, 'message': 'Kafka session not ready'})

        print(f"✅ Kafka session ID: {frames_record.kafka_session_id}")

        success = False

        print(f"🔍 KAFKA_AVAILABLE = {KAFKA_AVAILABLE}")

        if KAFKA_AVAILABLE:
            try:
                print("🚀 Initializing Kafka client...")
                kafka_client = KafkaFrameClient()

                if kafka_client.is_connected():
                    print("✅ Kafka client connected")

                    success = kafka_client.send_frame(
                        session_id=frames_record.kafka_session_id,
                        frame_number=frame_number,
                        frame_data_b64=frame_data,
                        width=width,
                        height=height
                    )

                    print(f"📤 Kafka send_frame result: {success}")

                    if success:
                        frames_record.total_frames = max(
                            frames_record.total_frames,
                            frame_number + 1
                        )
                        frames_record.save(update_fields=['total_frames'])
                        print("💾 Frame count updated")

                else:
                    print("❌ Kafka client NOT connected")

                kafka_client.close()
                print("🔒 Kafka client closed")

            except Exception as kafka_error:
                print("❌ Kafka Frame Error:", str(kafka_error))

        else:
            print("❌ KAFKA_AVAILABLE is False")

        return JsonResponse({
            'success': success,
            'frame_number': frame_number,
            'session_id': frames_record.kafka_session_id
        })

    except Exception as e:
        print("🚨 STREAM_FRAME ERROR:", str(e))
        return JsonResponse({'success': False})
# NEW VIDEO RECORDING ENDPOINTS

@csrf_exempt
@require_http_methods(["POST"])
def stream_video_chunk(request):
    """Stream video chunks to Kafka safely"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        # Get latest interview (ignore status)
        interview = Interview.objects.filter(
            student=request.user
        ).order_by('-id').first()

        if not interview:
            # Do NOT return 404 (prevents frontend spam)
            return JsonResponse({'success': False, 'message': 'No interview found'})

        # Parse JSON safely
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'})

        chunk_number = data.get('chunk_number', 0)
        video_data = data.get('video_data')
        chunk_size = data.get('chunk_size')
        timestamp = data.get('timestamp')
        mime_type = data.get('mime_type', 'video/webm')

        if not video_data:
            return JsonResponse({'success': False, 'message': 'Missing video data'})

        # Get or create InterviewFrames record
        frames_record, created = InterviewFrames.objects.get_or_create(
            interview=interview,
            defaults={
                'video_session_id': f"video_session_{interview.id}",
                'total_video_chunks': 0
            }
        )

        # Ensure session id exists
        if not frames_record.video_session_id:
            frames_record.video_session_id = f"video_session_{interview.id}"
            frames_record.save(update_fields=['video_session_id'])

        video_session_id = frames_record.video_session_id

        success = False

        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()

                if kafka_client.is_connected():
                    success = kafka_client.send_video_chunk(
    session_id=video_session_id,
    chunk_number=chunk_number,
    video_data_b64=video_data,
    chunk_size=chunk_size,
    timestamp=timestamp,
    mime_type=mime_type,
    interview_id=interview.id,
    user_id=request.user.id
)

                    if success:
                        frames_record.total_video_chunks = max(
                            frames_record.total_video_chunks,
                            chunk_number + 1
                        )
                        frames_record.save(update_fields=['total_video_chunks'])

                kafka_client.close()

            except Exception as kafka_error:
                print("VIDEO CHUNK KAFKA ERROR:", str(kafka_error))

        return JsonResponse({
            'success': success,
            'chunk_number': chunk_number,
            'video_session_id': video_session_id
        })

    except Exception as e:
        print("STREAM_VIDEO_CHUNK ERROR:", str(e))
        return JsonResponse({'success': False})


@csrf_exempt
@require_http_methods(["POST"])
def finalize_video_session(request):
    """Finalize video session when interview ends"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({'error': 'No active interview found'}, status=404)

        data = json.loads(request.body)
        total_chunks = data.get('total_chunks', 0)
        interview_id = data.get('interview_id')

        # Get frames record and update video session metadata
        frames_record = InterviewFrames.objects.filter(interview=interview).first()
        if frames_record and frames_record.video_session_id:
            # Update video recording metadata
            frames_record.total_video_chunks = total_chunks
            frames_record.video_recording_ended_at = timezone.now()

            # Calculate estimated duration (assuming ~3 seconds per chunk)
            if total_chunks > 0:
                frames_record.estimated_video_duration_seconds = total_chunks * 3

            frames_record.save()

            # Send session end marker to Kafka
            if KAFKA_AVAILABLE:
                try:
                    kafka_client = KafkaFrameClient()
                    if kafka_client.is_connected():
                        kafka_client.end_video_session(frames_record.video_session_id, total_chunks)
                        kafka_client.close()
                        logger.info(f"Video session finalized: {frames_record.video_session_id} with {total_chunks} chunks")
                except Exception as e:
                    logger.error(f"Failed to finalize video session: {e}")

        return JsonResponse({
            'success': True,
            'message': 'Video session finalized successfully',
            'total_chunks': total_chunks,
            'video_session_id': frames_record.video_session_id if frames_record else None
        })

    except Exception as e:
        logger.error(f"Error finalizing video session: {str(e)}")
        return JsonResponse({'error': 'Failed to finalize video session'}, status=500)

# REPLACE your existing get_kafka_video function with this:
# REPLACE your get_kafka_video function with this WORKING version:

@require_http_methods(["GET", "HEAD"])
def get_kafka_video(request, interview_id):
    """WORKING: Combine all chunks into one playable video"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)

        if not (request.user == interview.student or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        frames_record = InterviewFrames.objects.filter(interview=interview).first()
        if not frames_record:
            return JsonResponse({'error': 'No video session found'}, status=404)

        # Handle HEAD requests
        if request.method == 'HEAD':
            response = HttpResponse()
            response['Content-Type'] = 'video/webm'
            response['Accept-Ranges'] = 'bytes'
            return response

        # Get video chunks from Kafka
        session_ids_to_try = []
        if frames_record.video_session_id:
            session_ids_to_try.append(frames_record.video_session_id)
        if frames_record.kafka_session_id:
            session_ids_to_try.append(frames_record.kafka_session_id)

        video_chunks = None
        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                if kafka_client.is_connected():
                    for session_id in session_ids_to_try:
                        chunks = kafka_client.get_video_chunks(session_id)
                        if chunks:
                            video_chunks = chunks
                            break
                kafka_client.close()
            except Exception as e:
                logger.error(f"Kafka error: {e}")
                return JsonResponse({'error': 'Kafka service error'}, status=500)

        if not video_chunks:
            return JsonResponse({'error': 'No video chunks found'}, status=404)

        # Sort chunks and combine them
        sorted_chunks = sorted(video_chunks, key=lambda x: int(x.get('chunk_number', 0)))
        logger.info(f"Combining {len(sorted_chunks)} chunks into video")

        # WORKING APPROACH: Combine all chunks into one video
        combined_video_data = []
        successful_chunks = 0

        for i, chunk in enumerate(sorted_chunks):
            try:
                video_data_b64 = chunk.get('video_data', '')
                if not video_data_b64:
                    continue

                # Decode chunk
                video_data_b64 = video_data_b64.strip()
                missing_padding = len(video_data_b64) % 4
                if missing_padding:
                    video_data_b64 += '=' * (4 - missing_padding)

                video_data = base64.b64decode(video_data_b64)
                if len(video_data) > 0:
                    combined_video_data.append(video_data)
                    successful_chunks += 1

            except Exception as e:
                logger.warning(f"Failed to decode chunk {i}: {e}")
                continue

        if not combined_video_data:
            return JsonResponse({'error': 'No valid chunks found'}, status=404)

        # Combine all video data
        full_video = b''.join(combined_video_data)
        total_size = len(full_video)

        logger.info(f"✅ Combined {successful_chunks} chunks into {total_size / 1024 / 1024:.2f}MB video")

        # Return the complete video
        response = HttpResponse(full_video, content_type='video/webm')
        response['Content-Length'] = str(total_size)
        response['Accept-Ranges'] = 'bytes'
        response['Content-Disposition'] = f'inline; filename="interview_{interview_id}.webm"'
        response['Cache-Control'] = 'public, max-age=3600'

        return response

    except Exception as e:
        logger.error(f"Error serving video: {e}")
        return JsonResponse({'error': 'Server error'}, status=500)
# In your interview_system/views.py, update the get_video_info function:

@require_http_methods(["GET"])
def get_video_info(request, interview_id):
    """Get video information using video session ID"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)

        # Check permissions
        if not (request.user == interview.student or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        frames_record = InterviewFrames.objects.filter(interview=interview).first()
        if not frames_record or not frames_record.video_session_id:
            return JsonResponse({
                'success': False,
                'error': 'No video session found',
                'video_available': False,
                'total_chunks': 0,
                'interview_id': interview_id
            }, status=404)

        # Quick check: if we know there are 0 video chunks, return immediately
        if hasattr(frames_record, 'total_video_chunks') and frames_record.total_video_chunks == 0:
            return JsonResponse({
                'success': True,
                'interview_id': interview_id,
                'video_available': False,
                'total_chunks': 0,
                'video_url': f'/interview/api/kafka-video/{interview_id}/',
                'interview_info': {
                    'student_name': interview.student.get_full_name(),
                    'completed_at': interview.completed_at.isoformat() if interview.completed_at else None,
                    'attempt_number': interview.attempt_number,
                    'duration_estimate': 'No video recorded',
                    'interview_status': interview.status
                },
                'debug_info': {
                    'kafka_available': KAFKA_AVAILABLE,
                    'video_session_id': frames_record.video_session_id,  # ← ADD THIS
                    'frame_session_id': frames_record.kafka_session_id,  # ← ADD THIS
                    'error_message': 'No video chunks were recorded during this interview',
                    'interview_completed': interview.status == 'completed',
                    'quick_check': True
                }
            })

        # Get video chunk count from Kafka using video session ID
        chunk_count = 0
        kafka_available = False
        error_message = None

        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                if kafka_client.is_connected():
                    kafka_available = True

                    # Quick check with limited timeout
                    import threading
                    import time

                    result = {'chunks': []}

                    def get_chunks_with_timeout():
                        try:
                            result['chunks'] = kafka_client.get_video_chunks(frames_record.video_session_id)
                        except Exception as e:
                            result['error'] = str(e)

                    # Run with 20 second timeout
                    thread = threading.Thread(target=get_chunks_with_timeout)
                    thread.daemon = True
                    thread.start()
                    thread.join(timeout=20)

                    if thread.is_alive():
                        error_message = "Video chunk retrieval timed out (>20s)"
                        chunk_count = 0
                    elif 'error' in result:
                        error_message = result['error']
                        chunk_count = 0
                    else:
                        video_chunks = result['chunks']
                        chunk_count = len(video_chunks) if video_chunks else 0

                    kafka_client.close()
                    logger.info(f"Video info for interview {interview_id}: {chunk_count} chunks found")
                else:
                    error_message = "Kafka client not connected"

            except Exception as e:
                error_message = f"Error accessing Kafka: {str(e)}"
                logger.error(f"Error getting video info for interview {interview_id}: {e}")
        else:
            error_message = "Kafka not available"

        return JsonResponse({
            'success': True,
            'interview_id': interview_id,
            'video_available': chunk_count > 0,
            'total_chunks': chunk_count,
            'video_url': f'/interview/api/kafka-video/{interview_id}/',
            'interview_info': {
                'student_name': interview.student.get_full_name(),
                'completed_at': interview.completed_at.isoformat() if interview.completed_at else None,
                'attempt_number': interview.attempt_number,
                'duration_estimate': f'~{chunk_count * 3} seconds' if chunk_count > 0 else 'No video recorded',
                'interview_status': interview.status
            },
            'debug_info': {
                'kafka_available': kafka_available,
                'video_session_id': frames_record.video_session_id,
                'frame_session_id': frames_record.kafka_session_id,
                'total_video_chunks_db': frames_record.total_video_chunks,
                'error_message': error_message,
                'interview_completed': interview.status == 'completed'
            }
        })

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting video info for interview {interview_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to get video info'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def save_audio_response(request):
    """Save audio response to local storage and HDFS"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({'error': 'No active interview found'}, status=404)

        audio_file = request.FILES.get('audio')
        question_id = request.POST.get('questionId')

        if not audio_file or not question_id:
            return JsonResponse({'error': 'Missing audio file or question ID'}, status=400)

        # Save to local storage first
        local_path = None
        try:
            # Create local responses directory
            responses_dir = os.path.join(settings.BASE_DIR, 'audio_responses')
            if not os.path.exists(responses_dir):
                os.makedirs(responses_dir)

            # Create user-specific directory
            user_dir = os.path.join(responses_dir, f"user_{request.user.id}attempt{interview.attempt_number}")
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)

            # Save file locally
            filename = f"{question_id.replace('/', '')}{timezone.now().strftime('%Y%m%d_%H%M%S')}.webm"
            local_path = os.path.join(user_dir, filename)

            with open(local_path, 'wb') as f:
                for chunk in audio_file.chunks():
                    f.write(chunk)

            logger.info(f"Audio saved locally: {local_path}")

        except Exception as e:
            logger.error(f"Error saving audio locally: {e}")
            return JsonResponse({'error': 'Failed to save audio locally'}, status=500)

        # Try to save to HDFS (optional)
        hdfs_path = None
        try:
            hdfs_client = HDFSClient()
            if hdfs_client.is_connected():
                # Reset file pointer
                audio_file.seek(0)
                hdfs_path = hdfs_client.save_audio_response(
                    audio_file,
                    question_id,
                    request.user,
                    interview.attempt_number
                )
                logger.info(f"Audio also saved to HDFS: {hdfs_path}")
        except Exception as e:
            logger.warning(f"HDFS save failed (continuing with local): {e}")

        # Create response record
        response = InterviewResponse.objects.create(
            interview=interview,
            question=question_id,
            audio_file_path=hdfs_path or local_path,
            local_file_path=local_path
        )

        return JsonResponse({
            'success': True,
            'local_path': local_path,
            'hdfs_path': hdfs_path,
            'response_id': str(response.id)
        })

    except Exception as e:
        logger.error(f"Error saving audio response: {str(e)}")
        return JsonResponse({'error': 'Failed to save audio response'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_video_frames(request):
    """Upload video frames to Kafka (primary) and HDFS (backup) - Backward compatibility"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({'error': 'No active interview found'}, status=404)

        frames_data = json.loads(request.body)
        frames_list = frames_data.get('frames', [])

        if not frames_list:
            return JsonResponse({'error': 'No frames data provided'}, status=400)

        kafka_success = False
        hdfs_success = False
        session_id = None
        hdfs_path = None

        # Try Kafka first (primary storage)
        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                if kafka_client.is_connected():
                    # Start frame session
                    session_id = kafka_client.start_frame_session(
                        user=request.user,
                        interview=interview,
                        total_frames_estimate=len(frames_list)
                    )

                    if session_id:
                        # Send frames to Kafka
                        kafka_success = kafka_client.send_frames_batch(session_id, frames_list)

                        if kafka_success:
                            # End session
                            kafka_client.end_frame_session(session_id, len(frames_list))
                            logger.info(f"Frames successfully sent to Kafka: {session_id}")
                        else:
                            logger.error("Failed to send frames to Kafka")

                    kafka_client.close()
                else:
                    logger.warning("Kafka client not connected")

            except Exception as e:
                logger.error(f"Kafka processing failed: {e}")

        # Try HDFS as backup or primary if Kafka failed
        try:
            hdfs_client = HDFSClient()
            if hdfs_client.is_connected():
                hdfs_path = hdfs_client.save_frames(
                    frames_data,
                    request.user,
                    interview.attempt_number
                )
                hdfs_success = hdfs_path is not None
                if hdfs_success:
                    logger.info(f"Frames saved to HDFS: {hdfs_path}")
        except Exception as e:
            logger.warning(f"HDFS save failed: {e}")

        # Update interview frames record
        if kafka_success or hdfs_success:
            try:
                frames_record, created = InterviewFrames.objects.get_or_create(
                    interview=interview,
                    defaults={
                        'frames_file_path': hdfs_path,
                        'total_frames': len(frames_list),
                        'kafka_session_id': session_id,
                        'storage_method': 'kafka' if kafka_success else 'hdfs'
                    }
                )

                if not created:
                    frames_record.frames_file_path = hdfs_path
                    frames_record.total_frames = len(frames_list)
                    frames_record.kafka_session_id = session_id
                    frames_record.storage_method = 'kafka' if kafka_success else 'hdfs'
                    frames_record.save()

                logger.info(f"Frames record updated for interview {interview.id}")

            except Exception as e:
                logger.error(f"Failed to update interview frames record: {e}")

        # Return response
        response_data = {
            'success': kafka_success or hdfs_success,
            'message': 'Frames uploaded successfully',
            'storage_details': {
                'kafka_success': kafka_success,
                'kafka_session_id': session_id,
                'hdfs_success': hdfs_success,
                'hdfs_path': hdfs_path,
                'total_frames': len(frames_list),
                'primary_storage': 'kafka' if kafka_success else 'hdfs' if hdfs_success else 'none'
            }
        }

        if not (kafka_success or hdfs_success):
            response_data['error'] = 'Failed to store frames in both Kafka and HDFS'
            return JsonResponse(response_data, status=500)

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error uploading frames: {str(e)}")
        return JsonResponse({'error': 'Failed to upload frames'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def end_interview(request):
    """End the current interview and close both frame and video sessions"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({'error': 'No active interview found'}, status=404)

        # Get frames record with both session IDs
        frames_record = InterviewFrames.objects.filter(interview=interview).first()

        # End both Kafka sessions
        if frames_record and KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                if kafka_client.is_connected():
                    # End frame session if exists
                    if frames_record.kafka_session_id:
                        kafka_client.end_frame_session(
                            session_id=frames_record.kafka_session_id,
                            total_frames_sent=frames_record.total_frames
                        )
                        logger.info(f"Frame session ended: {frames_record.kafka_session_id}")

                    # End video session if exists
                    if frames_record.video_session_id:
                        kafka_client.end_video_session(
                            session_id=frames_record.video_session_id,
                            total_chunks=frames_record.total_video_chunks
                        )
                        logger.info(f"Video session ended: {frames_record.video_session_id}")

                    kafka_client.close()
            except Exception as e:
                logger.error(f"Failed to end Kafka sessions: {e}")

        # Get voice session to check completion state
        voice_session = VoiceInterviewSession.objects.filter(interview=interview).first()
        
        # Calculate interview duration
        duration_seconds = None
        if interview.started_at:
            duration_seconds = int((timezone.now() - interview.started_at).total_seconds())
        
        # Determine completion reason if not already set
        if not interview.completion_reason:
            if voice_session:
                if voice_session.current_question_number >= VOICE_INTERVIEW_CONFIG.get('MAX_QUESTIONS', 15):
                    interview.completion_reason = 'all_questions_answered'
                    interview.voice_interview_completed = True
                else:
                    interview.completion_reason = 'user_ended_early'
            else:
                interview.completion_reason = 'not_started'
        
        # Update completion tracking fields
        interview.status = 'completed'
        interview.completed_at = timezone.now()
        interview.interview_duration_seconds = duration_seconds
        if not interview.analysis_completed:
            interview.processing_status = 'pending'
        
        # Sync questions answered from voice session
        if voice_session:
            interview.questions_answered = voice_session.current_question_number
            interview.completion_percentage = (voice_session.current_question_number / interview.total_questions) * 100
            # End the voice session if still in progress
            if voice_session.session_status == 'in_progress':
                voice_session.complete_session(reason='user_ended' if interview.completion_reason == 'user_ended_early' else 'completed')
        
        interview.save()

        # Update final video recording metadata
        if frames_record:
            frames_record.video_recording_ended_at = timezone.now()
            frames_record.save()
            # Update interview data availability flags
            interview.has_video_recording = frames_record.total_video_chunks > 0
            interview.has_frame_data = frames_record.total_frames > 0
            interview.save(update_fields=['has_video_recording', 'has_frame_data'])

        if voice_session and voice_session.current_question_number >= interview.total_questions and not interview.analysis_completed:
            interview.processing_status = 'processing'
            interview.save(update_fields=['processing_status'])
            threading.Thread(
                target=_run_final_interview_analysis,
                args=(interview.id,),
                daemon=True,
            ).start()

        # NEW: Create and store complete interview session JSON
        try:
            from .session_manager import InterviewSessionManager
            session_manager = InterviewSessionManager()
            session_data = session_manager.create_session_json(interview.id)

            if session_data:
                logger.info(f"Interview session JSON created for interview {interview.id}")
            else:
                logger.error(f"Failed to create session JSON for interview {interview.id}")
        except Exception as e:
            logger.error(f"Error creating interview session JSON: {e}")

        # NOTE: Analysis is handled by Airflow DAG (consolidated_interview_processor_llm)
        # The DAG will pick up completed interviews and trigger:
        # - Dlib container for video/audio behavioral analysis
        # - Audio API for transcription and grading
        # - LLM-based report generation
        logger.info(f"Interview {interview.id} completed. Analysis will be triggered by Airflow DAG.")

        return JsonResponse({
            'success': True,
            'message': 'Interview completed successfully',
            'interview_id': interview.id,
            'completed_at': interview.completed_at.isoformat(),
            'total_frames': frames_record.total_frames if frames_record else 0,
            'total_video_chunks': frames_record.total_video_chunks if frames_record else 0,
            'redirect_url': '/'  # Redirect to root path
        })

    except Exception as e:
        logger.error(f"Error ending interview: {str(e)}")
        return JsonResponse({'error': 'Failed to end interview'}, status=500)

# Rest of your existing functions remain the same...
@login_required
@require_http_methods(["GET"])
def get_current_interview(request):
    """Get the current active interview for the user"""
    try:
        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({
                'error': 'No active interview found'
            }, status=404)

        return JsonResponse({
            'success': True,
            'interview_id': interview.id,
            'status': interview.status,
            'started_at': interview.started_at.isoformat() if interview.started_at else None
        })

    except Exception as e:
        logger.error(f"Error getting current interview: {e}")
        return JsonResponse({
            'error': 'Failed to get current interview'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def request_interview(request):
    """Request a new interview"""
    try:
        # Check if user already has an active request or approved interview
        existing_interview = Interview.objects.filter(
            student=request.user,
            status__in=['requested', 'approved', 'in_progress']
        ).first()

        if existing_interview:
            if existing_interview.status == 'requested':
                return JsonResponse({
                    'error': 'You already have a pending interview request'
                }, status=400)
            elif existing_interview.status == 'approved':
                return JsonResponse({
                    'error': 'You have an approved interview. Please start it first.'
                }, status=400)
            elif existing_interview.status == 'in_progress':
                return JsonResponse({
                    'error': 'You have an interview in progress'
                }, status=400)

        # Get the next attempt number
        last_interview = Interview.objects.filter(student=request.user).order_by('-attempt_number').first()
        attempt_number = (last_interview.attempt_number + 1) if last_interview else 1

        # Create new interview request
        interview = Interview.objects.create(
            student=request.user,
            status='requested',
            attempt_number=attempt_number,
            requested_at=timezone.now()
        )

        logger.info(f"Interview request created: {interview.id} for user {request.user.id}")

        return JsonResponse({
            'success': True,
            'message': 'Interview request submitted successfully. Please wait for admin approval.',
            'interview_id': interview.id
        })

    except Exception as e:
        logger.error(f"Error requesting interview for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'error': 'Failed to submit interview request'
        }, status=500)


@login_required
def get_all_interviews(request):
    """Get all interviews for the current user"""
    try:
        interviews = Interview.objects.filter(student=request.user).order_by('-created_at')

        interview_data = []
        for interview in interviews:
            # Calculate time remaining for approved interviews
            time_remaining = 0
            if interview.status == 'approved' and interview.expires_at:
                remaining_seconds = (interview.expires_at - timezone.now()).total_seconds()
                time_remaining = max(0, int(remaining_seconds / 60))  # Convert to minutes

                # Auto-expire if time is up
                if time_remaining <= 0 and interview.status == 'approved':
                    interview.status = 'expired'
                    interview.save()

            interview_data.append({
                'id': interview.id,
                'status': interview.status,
                'attempt_number': interview.attempt_number,
                'created_at': interview.created_at.isoformat(),
                'requested_at': interview.requested_at.isoformat() if interview.requested_at else None,
                'approved_at': interview.approved_at.isoformat() if interview.approved_at else None,
                'started_at': interview.started_at.isoformat() if interview.started_at else None,
                'completed_at': interview.completed_at.isoformat() if interview.completed_at else None,
                'scheduled_at': interview.scheduled_at.isoformat() if interview.scheduled_at else None,
                'expires_at': interview.expires_at.isoformat() if interview.expires_at else None,
                'time_remaining': time_remaining,
                'overall_score': interview.overall_score,
                'technical_score': interview.technical_score,
                'communication_score': interview.communication_score,
                'confidence_score': interview.confidence_score,
                'cheating_detected': interview.cheating_detected,
                'analysis_completed': interview.analysis_completed,
                'admin_notes': interview.admin_notes,
            })

        return JsonResponse(interview_data, safe=False)

    except Exception as e:
        logger.error(f"Error getting interviews for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'error': 'Failed to load interviews'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_interview_status(request, interview_id):
    """Get status of a specific interview"""
    try:
        interview = get_object_or_404(Interview, id=interview_id, student=request.user)

        return JsonResponse({
            'id': interview.id,
            'status': interview.status,
            'started_at': interview.started_at.isoformat() if interview.started_at else None,
            'completed_at': interview.completed_at.isoformat() if interview.completed_at else None,
            'overall_score': interview.overall_score,
            'analysis_completed': interview.analysis_completed,
        })

    except Exception as e:
        logger.error(f"Error getting interview status: {e}")
        return JsonResponse({'error': 'Failed to get interview status'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_frame_status(request, interview_id):
    """Get frame processing status"""
    try:
        interview = get_object_or_404(Interview, id=interview_id, student=request.user)

        # Get frames record
        frames_record = InterviewFrames.objects.filter(interview=interview).first()

        if not frames_record:
            return JsonResponse({'error': 'No frames record found'}, status=404)

        status_data = {
            'interview_id': interview.id,
            'total_frames': frames_record.total_frames,
            'storage_method': getattr(frames_record, 'storage_method', 'hdfs'),
            'kafka_session_id': getattr(frames_record, 'kafka_session_id', None),
            'hdfs_path': frames_record.frames_file_path,
            'created_at': frames_record.created_at.isoformat() if hasattr(frames_record, 'created_at') else None
        }

        return JsonResponse(status_data)

    except Exception as e:
        logger.error(f"Error getting frame status: {e}")
        return JsonResponse({'error': 'Failed to get frame status'}, status=500)


@login_required
@require_http_methods(["GET"])
def get_frame_analysis(request, interview_id):
    """Get detailed frame analysis results"""
    try:
        interview = get_object_or_404(Interview, id=interview_id, student=request.user)

        frames_record = InterviewFrames.objects.filter(interview=interview).first()
        if not frames_record:
            return JsonResponse({'error': 'No frames record found for this interview'}, status=404)

        # For now, return basic info - this can be extended when Kafka MySQL integration is ready
        return JsonResponse({
            'interview_id': interview.id,
            'frames_available': frames_record.total_frames,
            'analysis_status': 'pending',  # This will be updated when frame processor is ready
            'message': 'Frame analysis will be available once processing is complete'
        })

    except Exception as e:
        logger.error(f"Error getting frame analysis: {e}")
        return JsonResponse({'error': 'Failed to get frame analysis'}, status=500)


@staff_member_required
def get_interviews_list(request):
    """Get all interviews for admin dashboard with complete availability info"""
    try:
        interviews = Interview.objects.select_related('student', 'approved_by').order_by('-created_at')

        interview_data = []
        for interview in interviews:
            # Get student profile for availability information
            student_profile = getattr(interview.student, 'student_profile', None)

            # Calculate time remaining for approved interviews
            time_remaining = 0
            if interview.status == 'approved' and interview.expires_at:
                remaining_seconds = (interview.expires_at - timezone.now()).total_seconds()
                time_remaining = max(0, int(remaining_seconds / 60))  # Convert to minutes

                # Auto-expire if time is up
                if time_remaining <= 0 and interview.status == 'approved':
                    interview.status = 'expired'
                    interview.save()

            interview_data.append({
                # Basic interview info
                'id': interview.id,
                'status': interview.status,
                'attempt_number': interview.attempt_number,
                'created_at': interview.created_at.isoformat(),
                'requested_at': interview.requested_at.isoformat() if interview.requested_at else None,
                'approved_at': interview.approved_at.isoformat() if interview.approved_at else None,
                'started_at': interview.started_at.isoformat() if interview.started_at else None,
                'completed_at': interview.completed_at.isoformat() if interview.completed_at else None,
                'scheduled_at': interview.scheduled_at.isoformat() if interview.scheduled_at else None,
                'expires_at': interview.expires_at.isoformat() if interview.expires_at else None,
                'time_remaining': time_remaining,

                # Scores and analysis
                'overall_score': interview.overall_score,
                'technical_score': interview.technical_score,
                'communication_score': interview.communication_score,
                'confidence_score': interview.confidence_score,
                'cheating_detected': interview.cheating_detected,
                'analysis_completed': interview.analysis_completed,
                'admin_notes': interview.admin_notes,

                # Student basic info
                'student_name': interview.student.get_full_name(),
                'student_email': interview.student.email,
                'student_id': student_profile.student_id if student_profile else 'N/A',
                'approved_by_name': interview.approved_by.get_full_name() if interview.approved_by else None,

                # Add complete availability information
                'student_batch_id': student_profile.batch_id if student_profile else 'Not Set',
                'student_preference': student_profile.get_interview_preference_display() if student_profile and student_profile.interview_preference else 'Not Set',
                'has_complete_availability': student_profile.has_complete_availability() if student_profile else False,
                'availability_summary': student_profile.get_availability_summary() if student_profile else 'Not Available',
                'student_availability_summary': student_profile.get_availability_summary() if student_profile else 'Not Available',
                'availability_updated_at': student_profile.availability_updated_at.strftime('%Y-%m-%d %H:%M') if student_profile and student_profile.availability_updated_at else 'Never',

                # Add detailed availability slots
                'student_availability_slots': student_profile.availability_slots if student_profile and student_profile.availability_slots else [],
                'availability_slots': student_profile.availability_slots if student_profile and student_profile.availability_slots else [],

                # Additional fields for consistency
                'batch_id': student_profile.batch_id if student_profile else 'Not Set',
                'interview_preference': student_profile.interview_preference if student_profile else None,
            })

        return JsonResponse(interview_data, safe=False)

    except Exception as e:
        logger.error(f"Error getting interviews list: {str(e)}")
        return JsonResponse({
            'error': 'Failed to load interviews'
        }, status=500)



@staff_member_required
@require_http_methods(["POST"])
def approve_interview(request, interview_id):
    """Approve interview with proper IST handling"""
    try:
        data = json.loads(request.body)
        interview = get_object_or_404(Interview, id=interview_id)

        if interview.status != 'requested':
            return JsonResponse({'error': 'Interview is not in requested status'}, status=400)

        scheduled_at_str = data.get('scheduled_at')
        if not scheduled_at_str:
            return JsonResponse({'error': 'Scheduled date and time is required'}, status=400)

        # Parse datetime and treat as IST input
        try:
            # Parse the datetime string (format: "2025-07-29T15:30")
            scheduled_naive = datetime.strptime(scheduled_at_str, '%Y-%m-%dT%H:%M')

            # Treat admin input as IST time
            ist_tz = pytz.timezone('Asia/Kolkata')
            scheduled_ist = ist_tz.localize(scheduled_naive)

            # Convert to UTC for database storage
            scheduled_utc = scheduled_ist.astimezone(pytz.UTC)

            print(f"Admin entered: {scheduled_at_str}")
            print(f"Treated as IST: {scheduled_ist}")
            print(f"Converted to UTC for DB: {scheduled_utc}")

        except ValueError as e:
            return JsonResponse({'error': f'Invalid date format: {e}. Use YYYY-MM-DDTHH:MM'}, status=400)

        # Check if in future (compare in IST)
        now_ist = get_ist_now()
        if scheduled_ist <= now_ist:
            return JsonResponse({
                'error': f'Scheduled time must be in future. Current IST: {format_ist_time(now_ist)}'
            }, status=400)

        # Store UTC times in database
        interview.status = 'approved'
        interview.approved_at = timezone.now()
        interview.approved_by = request.user
        interview.scheduled_at = scheduled_utc  # Store UTC in DB
        interview.expires_at = scheduled_utc + timedelta(minutes=60)  # 60 min window
        interview.admin_notes = data.get('admin_notes', '')
        interview.save()

        logger.info(f"Interview {interview_id} scheduled for {format_ist_time(scheduled_ist)} IST")

        return JsonResponse({
            'success': True,
            'message': f'Interview scheduled for {format_ist_time(scheduled_ist)}',
            'scheduled_at_ist': format_ist_time(scheduled_ist),
            'expires_at_ist': format_ist_time(scheduled_ist + timedelta(minutes=60))
        })

    except Exception as e:
        logger.error(f"Error approving interview {interview_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to approve interview'}, status=500)


@staff_member_required
@require_http_methods(["POST"])
def reject_interview(request, interview_id):
    """Reject an interview request"""
    try:
        data = json.loads(request.body)
        interview = get_object_or_404(Interview, id=interview_id)

        if interview.status != 'requested':
            return JsonResponse({
                'error': 'Interview is not in requested status'
            }, status=400)

        # Set status to 'cancelled' for email DAG detection
        interview.status = 'cancelled'
        interview.approved_by = request.user

        # Ensure admin_notes is set for rejection reason
        admin_notes = data.get('admin_notes', '').strip()
        if not admin_notes:
            admin_notes = 'Request rejected by admin - Please contact support for more details'

        interview.admin_notes = admin_notes
        interview.save()

        # Log the rejection for email DAG detection
        logger.info(f"📧 Interview {interview_id} REJECTED - Email DAG should detect this change")
        logger.info(f"   Student: {interview.student.get_full_name()}")
        logger.info(f"   Email: {interview.student.email}")
        logger.info(f"   Reason: {admin_notes}")
        logger.info(f"   Rejected at: {timezone.now()}")

        return JsonResponse({
            'success': True,
            'message': 'Interview request rejected. Student will receive email notification within 2 minutes.',
            'email_notification': 'Rejection email will be sent automatically'
        })

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error rejecting interview {interview_id}: {str(e)}")
        return JsonResponse({'error': 'Failed to reject interview'}, status=500)


@staff_member_required
@require_http_methods(["GET"])
def get_email_notification_status(request, interview_id):
    """Get email notification status for an interview"""
    try:
        from django.db import connection

        # Query the email notifications table created by the DAG
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    notification_type,
                    email_sent,
                    email_sent_at,
                    email_status,
                    error_message,
                    retry_count,
                    created_at
                FROM interview_email_notifications
                WHERE interview_id = %s
                ORDER BY created_at DESC
            """, [interview_id])

            notifications = []
            for row in cursor.fetchall():
                notifications.append({
                    'type': row[0],
                    'email_sent': row[1],
                    'sent_at': row[2].isoformat() if row[2] else None,
                    'status': row[3],
                    'error': row[4],
                    'retries': row[5],
                    'created_at': row[6].isoformat() if row[6] else None
                })

        return JsonResponse({
            'interview_id': interview_id,
            'notifications': notifications,
            'total_notifications': len(notifications)
        })

    except Exception as e:
        # If table doesn't exist yet, return empty status
        return JsonResponse({
            'interview_id': interview_id,
            'notifications': [],
            'message': 'Email notification system not yet initialized'
        })

@staff_member_required
@require_http_methods(["POST"])
def create_interview_session_json(request, interview_id):
    """Manually create interview session JSON"""
    try:
        from .session_manager import InterviewSessionManager

        session_manager = InterviewSessionManager()
        session_data = session_manager.create_session_json(interview_id)

        if session_data:
            return JsonResponse({
                'success': True,
                'message': 'Session JSON created successfully',
                'session_data': session_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create session JSON'
            }, status=500)

    except Exception as e:
        logger.error(f"Error creating session JSON: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@staff_member_required
@require_http_methods(["POST"])
def manually_trigger_email_notification(request, interview_id):
    """Manually trigger email notification for testing purposes"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)

        # Force update the interview to trigger email DAG detection
        if interview.status == 'approved':
            # Touch the approved_at timestamp to make it recent
            interview.approved_at = timezone.now()
            interview.save()
            notification_type = 'approval'

        elif interview.status == 'cancelled':
            # Touch the updated_at timestamp to make it recent
            interview.save()  # This updates the updated_at field
            notification_type = 'rejection'

        else:
            return JsonResponse({
                'success': False,
                'error': f'Interview status "{interview.status}" is not eligible for email notifications'
            }, status=400)

        logger.info(f"📧 Manually triggered {notification_type} email for interview {interview_id}")

        return JsonResponse({
            'success': True,
            'message': f'Email notification manually triggered for {notification_type}. Check DAG logs in 2-3 minutes.',
            'interview_id': interview_id,
            'notification_type': notification_type,
            'student_email': interview.student.email
        })

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)
    except Exception as e:
        logger.error(f"❌ Error manually triggering email for interview {interview_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
@require_http_methods(["GET"])
def diagnostic_kafka_status(request):
    """Diagnostic view to check Kafka and video system status"""
    try:
        diagnostic_data = {
            'timestamp': timezone.now().isoformat(),
            'kafka_available': KAFKA_AVAILABLE,
            'kafka_connection': None,
            'recent_interviews': [],
            'statistics': {},
            'errors': []
        }

        # Test Kafka connection
        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                diagnostic_data['kafka_connection'] = {
                    'connected': kafka_client.is_connected(),
                    'config': kafka_client.config if hasattr(kafka_client, 'config') else None
                }

                if kafka_client.is_connected():
                    # Get topic info
                    diagnostic_data['topics_info'] = kafka_client.get_topic_info()

                    # Test connection
                    test_result = kafka_client.test_connection()
                    diagnostic_data['connection_test'] = test_result

                kafka_client.close()

            except Exception as e:
                diagnostic_data['errors'].append(f"Kafka connection error: {str(e)}")
        else:
            diagnostic_data['errors'].append("Kafka not available - kafka-python not installed")

        # Get recent interviews with video data
        recent_interviews = Interview.objects.filter(
            status__in=['completed', 'in_progress']
        ).select_related('student').order_by('-created_at')[:10]

        for interview in recent_interviews:
            frames_record = InterviewFrames.objects.filter(interview=interview).first()

            interview_data = {
                'id': interview.id,
                'student': interview.student.get_full_name(),
                'status': interview.status,
                'created_at': interview.created_at.isoformat(),
                'completed_at': interview.completed_at.isoformat() if interview.completed_at else None,
                'frames_record_exists': frames_record is not None,
                'kafka_session_id': frames_record.kafka_session_id if frames_record else None,
                'total_frames': frames_record.total_frames if frames_record else 0,
                'storage_method': getattr(frames_record, 'storage_method', 'unknown') if frames_record else None,
                'video_chunks_available': 0
            }

            # Try to get video chunk count
            if frames_record and frames_record.kafka_session_id and KAFKA_AVAILABLE:
                try:
                    kafka_client = KafkaFrameClient()
                    if kafka_client.is_connected():
                        chunks = kafka_client.get_video_chunks(frames_record.kafka_session_id)
                        interview_data['video_chunks_available'] = len(chunks) if chunks else 0

                        if chunks:
                            total_size = sum(chunk.get('chunk_size', 0) for chunk in chunks)
                            interview_data['total_video_size_mb'] = round(total_size / 1024 / 1024, 2)

                    kafka_client.close()
                except Exception as e:
                    interview_data['video_error'] = str(e)

            diagnostic_data['recent_interviews'].append(interview_data)

        return JsonResponse(diagnostic_data, json_dumps_params={'indent': 2})

    except Exception as e:
        logger.error(f"Error in diagnostic view: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)
# Add this new endpoint to your views.py

# Add this to your interview_system/views.py (if not already added)

@require_http_methods(["GET"])
def get_video_chunk(request, interview_id, chunk_number):
    """Get a specific video chunk by number"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)

        if not (request.user == interview.student or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        frames_record = InterviewFrames.objects.filter(interview=interview).first()
        if not frames_record:
            return JsonResponse({'error': 'No video session found'}, status=404)

        # Get video chunks from Kafka
        session_ids_to_try = []
        if frames_record.video_session_id:
            session_ids_to_try.append(frames_record.video_session_id)
        if frames_record.kafka_session_id:
            session_ids_to_try.append(frames_record.kafka_session_id)

        target_chunk = None
        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                if kafka_client.is_connected():
                    for session_id in session_ids_to_try:
                        chunks = kafka_client.get_video_chunks(session_id)
                        if chunks:
                            # Find the specific chunk
                            for chunk in chunks:
                                if int(chunk.get('chunk_number', -1)) == int(chunk_number):
                                    target_chunk = chunk
                                    break
                            if target_chunk:
                                break
                kafka_client.close()
            except Exception as e:
                logger.error(f"Kafka error: {e}")
                return JsonResponse({'error': 'Kafka service error'}, status=500)

        if not target_chunk:
            return JsonResponse({'error': f'Chunk {chunk_number} not found'}, status=404)

        try:
            # Decode the specific chunk
            video_data_b64 = target_chunk.get('video_data', '')
            if not video_data_b64:
                return JsonResponse({'error': 'Empty chunk data'}, status=404)

            # Fix base64 padding
            missing_padding = len(video_data_b64) % 4
            if missing_padding:
                video_data_b64 += '=' * (4 - missing_padding)

            video_data = base64.b64decode(video_data_b64)

            # Return the chunk with proper headers
            response = HttpResponse(video_data, content_type='video/webm')
            response['Content-Length'] = str(len(video_data))
            response['Accept-Ranges'] = 'bytes'
            response['Content-Disposition'] = f'inline; filename="chunk_{chunk_number}.webm"'

            # Add chunk metadata headers
            response['X-Chunk-Number'] = str(chunk_number)
            response['X-Chunk-Size'] = str(target_chunk.get('chunk_size', len(video_data)))
            response['X-Chunk-Timestamp'] = str(target_chunk.get('timestamp', ''))

            logger.info(f"Serving chunk {chunk_number} for interview {interview_id} ({len(video_data)} bytes)")
            return response

        except Exception as e:
            logger.error(f"Error decoding chunk {chunk_number}: {e}")
            return JsonResponse({'error': 'Failed to decode chunk'}, status=500)

    except Exception as e:
        logger.error(f"Error getting chunk {chunk_number}: {e}")
        return JsonResponse({'error': 'Server error'}, status=500)

# REPLACE your get_video_manifest function with this CORRECTED version:

# Make sure your views.py has this EXACT function:

@require_http_methods(["GET"])
def get_video_manifest(request, interview_id):
    """Get video manifest with CORRECTED URLs"""
    try:
        # DEBUG LOG
        logger.info(f"🔍 get_video_manifest called for interview {interview_id}")

        interview = get_object_or_404(Interview, id=interview_id)

        if not (request.user == interview.student or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        frames_record = InterviewFrames.objects.filter(interview=interview).first()
        if not frames_record:
            return JsonResponse({'error': 'No video session found'}, status=404)

        # Get video chunks from Kafka
        session_ids_to_try = []
        if frames_record.video_session_id:
            session_ids_to_try.append(frames_record.video_session_id)
        if frames_record.kafka_session_id:
            session_ids_to_try.append(frames_record.kafka_session_id)

        video_chunks = []
        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                if kafka_client.is_connected():
                    for session_id in session_ids_to_try:
                        chunks = kafka_client.get_video_chunks(session_id)
                        if chunks:
                            video_chunks = chunks
                            break
                kafka_client.close()
            except Exception as e:
                logger.error(f"Kafka error: {e}")
                return JsonResponse({'error': 'Kafka service error'}, status=500)

        if not video_chunks:
            return JsonResponse({'error': 'No video chunks found'}, status=404)

        # Sort chunks and create manifest
        sorted_chunks = sorted(video_chunks, key=lambda x: int(x.get('chunk_number', 0)))

        manifest = {
            'interview_id': interview_id,
            'total_chunks': len(sorted_chunks),
            'chunks': [],
            'debug_info': 'NEW MANIFEST FUNCTION WORKING'  # DEBUG MARKER
        }

        total_size = 0
        for chunk in sorted_chunks:
            chunk_info = {
                'chunk_number': chunk.get('chunk_number'),
                'chunk_size': chunk.get('chunk_size', 0),
                'timestamp': chunk.get('timestamp'),
                'mime_type': chunk.get('mime_type', 'video/webm'),
                # CORRECTED URL FORMAT
                'url': f'/interview/api/kafka-video/{interview_id}/?chunk={chunk.get("chunk_number")}'
            }
            manifest['chunks'].append(chunk_info)
            total_size += chunk.get('chunk_size', 0)

        manifest['total_size'] = total_size
        manifest['estimated_duration'] = len(sorted_chunks) * 3

        # DEBUG LOG
        logger.info(f"✅ Generated manifest with {len(sorted_chunks)} chunks using NEW URL format")
        logger.info(f"🔗 Sample URL: {manifest['chunks'][0]['url'] if manifest['chunks'] else 'No chunks'}")

        return JsonResponse(manifest)

    except Exception as e:
        logger.error(f"Error generating manifest: {e}")
        return JsonResponse({'error': 'Server error'}, status=500)

# Add this NEW endpoint to your views.py

@require_http_methods(["GET"])
def get_reconstructed_video(request, interview_id):
    """Reconstruct video with proper WebM headers"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)

        if not (request.user == interview.student or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        frames_record = InterviewFrames.objects.filter(interview=interview).first()
        if not frames_record:
            return JsonResponse({'error': 'No video session found'}, status=404)

        # Get video chunks from Kafka
        session_ids_to_try = []
        if frames_record.video_session_id:
            session_ids_to_try.append(frames_record.video_session_id)
        if frames_record.kafka_session_id:
            session_ids_to_try.append(frames_record.kafka_session_id)

        video_chunks = None
        if KAFKA_AVAILABLE:
            try:
                kafka_client = KafkaFrameClient()
                if kafka_client.is_connected():
                    for session_id in session_ids_to_try:
                        chunks = kafka_client.get_video_chunks(session_id)
                        if chunks:
                            video_chunks = chunks
                            break
                kafka_client.close()
            except Exception as e:
                logger.error(f"Kafka error: {e}")
                return JsonResponse({'error': f'Kafka service error: {str(e)}'}, status=500)

        if not video_chunks:
            return JsonResponse({'error': 'No video chunks found in Kafka'}, status=404)

        # Sort chunks by chunk_number
        sorted_chunks = sorted(video_chunks, key=lambda x: int(x.get('chunk_number', 0)))
        logger.info(f"Found {len(sorted_chunks)} chunks for reconstruction")

        # IMPROVED: Reconstruct video with better handling
        video_parts = []
        successful_chunks = 0

        for i, chunk in enumerate(sorted_chunks):
            try:
                video_data_b64 = chunk.get('video_data', '')
                if not video_data_b64:
                    logger.warning(f"Chunk {i} has no video data, skipping")
                    continue

                # Clean and decode base64
                video_data_b64 = video_data_b64.strip()
                missing_padding = len(video_data_b64) % 4
                if missing_padding:
                    video_data_b64 += '=' * (4 - missing_padding)

                # Try decoding
                try:
                    video_data = base64.b64decode(video_data_b64)
                except Exception as decode_error:
                    logger.warning(f"Failed to decode chunk {i}: {decode_error}")
                    continue

                if len(video_data) > 0:
                    video_parts.append(video_data)
                    successful_chunks += 1

                    # Log progress every 25 chunks
                    if (i + 1) % 25 == 0:
                        logger.info(f"Processed {i + 1}/{len(sorted_chunks)} chunks")

            except Exception as e:
                logger.warning(f"Error processing chunk {i}: {e}")
                continue

        if not video_parts:
            return JsonResponse({'error': 'No valid video chunks could be decoded'}, status=404)

        logger.info(f"Successfully decoded {successful_chunks}/{len(sorted_chunks)} chunks")

        # Combine all video parts
        try:
            combined_video = b''.join(video_parts)
            total_size = len(combined_video)

            if total_size == 0:
                return JsonResponse({'error': 'Combined video is empty'}, status=404)

            logger.info(f"Combined video size: {total_size / 1024 / 1024:.2f} MB")

            # Create response with proper headers for video streaming
            response = HttpResponse(combined_video, content_type='video/webm')
            response['Content-Length'] = str(total_size)
            response['Accept-Ranges'] = 'bytes'
            response['Content-Disposition'] = f'inline; filename="interview_{interview_id}_reconstructed.webm"'

            # Add video-specific headers
            response['X-Video-Chunks'] = str(successful_chunks)
            response['X-Total-Size'] = str(total_size)
            response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour

            # IMPORTANT: Try different content types if WebM doesn't work
            # response['Content-Type'] = 'application/octet-stream'  # Force download to test

            logger.info(f"✅ Successfully serving reconstructed video: {total_size} bytes from {successful_chunks} chunks")
            return response

        except Exception as e:
            logger.error(f"Error combining video parts: {e}")
            return JsonResponse({'error': f'Failed to combine video: {str(e)}'}, status=500)

    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)
    except Exception as e:
        logger.error(f"Error reconstructing video: {e}")
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


# ALSO: Add a simple download endpoint for testing
@require_http_methods(["GET"])
def download_video_file(request, interview_id):
    """Force download video file for testing"""
    try:
        # Use the same logic as above but force download
        response = get_reconstructed_video(request, interview_id)

        if isinstance(response, HttpResponse) and response.status_code == 200:
            # Change headers to force download
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = f'attachment; filename="interview_{interview_id}.webm"'
            logger.info(f"Forcing download of video file for interview {interview_id}")

        return response

    except Exception as e:
        logger.error(f"Error in download endpoint: {e}")
        return JsonResponse({'error': f'Download failed: {str(e)}'}, status=500)

@require_http_methods(["GET"])
def get_kafka_chunks_direct(request, session_id):
    try:
        if not KAFKA_AVAILABLE:
            return JsonResponse({'error': 'Kafka not available'}, status=500)

        kafka_client = KafkaFrameClient()

        if kafka_client.is_connected():
            chunks = kafka_client.get_video_chunks(session_id)
            kafka_client.close()

            return JsonResponse({
                'success': True,
                'session_id': session_id,
                'chunks': chunks,
                'total_chunks': len(chunks)
            })
        else:
            return JsonResponse({'error': 'Kafka not connected'}, status=500)

    except Exception as e:
        logger.error(f"Error fetching chunks: {e}")
        return JsonResponse({'error': str(e)}, status=500)


# Add this class after your existing imports and before your existing classes
class SpeechToText:
    """Handles speech-to-text conversion with local Whisper preferred."""

    _model = None
    _provider = None
    _model_lock = threading.Lock()

    def __init__(self):
        self.config = getattr(settings, 'STT_CONFIG', {})
        self.preferred_provider = self.config.get('PROVIDER', 'faster_whisper')
        self.language = self.config.get('LANGUAGE', 'en')
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
        self._initialize_provider()

    def convert_audio_to_text(self, audio_data: bytes) -> str:
        try:
            logger.info(f"Processing {len(audio_data)} bytes with {self._provider} STT")

            if self._provider == 'faster_whisper':
                return self._convert_with_faster_whisper(audio_data)

            if self._provider == 'whisper':
                return self._convert_with_openai_whisper(audio_data)

            return self._convert_with_gemini(audio_data)

        except Exception as e:
            logger.error(f"STT error using {self._provider}: {e}")
            return None

    def _initialize_provider(self):
        with self._model_lock:
            if self.__class__._provider is not None:
                return

            provider_order = [self.preferred_provider, 'whisper', 'gemini']
            for provider in provider_order:
                if provider == 'faster_whisper' and self._try_init_faster_whisper():
                    return
                if provider == 'whisper' and self._try_init_openai_whisper():
                    return
                if provider == 'gemini' and self.client:
                    self.__class__._provider = 'gemini'
                    logger.info("STT provider initialized: Gemini")
                    return

            raise ValueError("No STT provider is available. Install faster-whisper or configure Gemini.")

    def _try_init_faster_whisper(self):
        try:
            from faster_whisper import WhisperModel

            self.__class__._model = WhisperModel(
                self.config.get('MODEL_SIZE', 'base.en'),
                device=self.config.get('DEVICE', 'cpu'),
                compute_type=self.config.get('COMPUTE_TYPE', 'int8'),
                cpu_threads=self.config.get('CPU_THREADS', 4),
                num_workers=self.config.get('NUM_WORKERS', 1),
            )
            self.__class__._provider = 'faster_whisper'
            logger.info(
                "STT provider initialized: faster-whisper (%s, %s, %s)",
                self.config.get('MODEL_SIZE', 'base.en'),
                self.config.get('DEVICE', 'cpu'),
                self.config.get('COMPUTE_TYPE', 'int8'),
            )
            return True
        except Exception as exc:
            logger.warning(f"faster-whisper unavailable: {exc}")
            return False

    def _try_init_openai_whisper(self):
        try:
            import whisper

            self.__class__._model = whisper.load_model(self.config.get('MODEL_SIZE', 'base.en'))
            self.__class__._provider = 'whisper'
            logger.info("STT provider initialized: openai-whisper (%s)", self.config.get('MODEL_SIZE', 'base.en'))
            return True
        except Exception as exc:
            logger.warning(f"openai-whisper unavailable: {exc}")
            return False

    def _convert_with_faster_whisper(self, audio_data: bytes) -> str:
        audio_path = self._write_temp_audio_file(audio_data)
        try:
            segments, _info = self._model.transcribe(
                audio_path,
                language=self.language,
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
                vad_filter=True,
            )
            transcription = " ".join(segment.text.strip() for segment in segments).strip()
            if transcription:
                logger.info(f"faster-whisper transcription: {transcription}")
            return transcription or None
        finally:
            self._cleanup_temp_file(audio_path)

    def _convert_with_openai_whisper(self, audio_data: bytes) -> str:
        audio_path = self._write_temp_audio_file(audio_data)
        try:
            result = self._model.transcribe(
                audio_path,
                language=self.language,
                fp16=False,
                condition_on_previous_text=False,
            )
            transcription = (result.get('text') or '').strip()
            if transcription:
                logger.info(f"openai-whisper transcription: {transcription}")
            return transcription or None
        finally:
            self._cleanup_temp_file(audio_path)

    def _convert_with_gemini(self, audio_data: bytes) -> str:
        if not self.client:
            return None

        from google.genai import types

        response = self.client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(
                    data=audio_data,
                    mime_type="audio/webm",
                ),
                "Transcribe this audio clearly. Return only the spoken words."
            ],
        )

        transcription = response.text.strip() if response.text else None

        if not transcription or len(transcription) < 2:
            logger.warning("No clear speech detected")
            return None

        logger.info(f"Gemini transcription: {transcription}")
        return transcription

    def _write_temp_audio_file(self, audio_data: bytes):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
            temp_audio.write(audio_data)
            return temp_audio.name

    def _cleanup_temp_file(self, path):
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except OSError as exc:
            logger.warning(f"Failed to delete temp audio file {path}: {exc}")



# Voice Interview Agent Class
# Replace your existing VoiceInterviewAgent class with this:
class VoiceInterviewAgent:
    """Voice interview agent with DeepSeek LLM integration and Gemini STT"""

    def __init__(self):
        self.api_key = VOICE_INTERVIEW_CONFIG['OPENROUTER_API_KEY']
        self.base_url = VOICE_INTERVIEW_CONFIG['DEEPSEEK_BASE_URL']
        self.model = VOICE_INTERVIEW_CONFIG['DEEPSEEK_MODEL']
        self.question_stages = VOICE_INTERVIEW_CONFIG['QUESTION_STAGES']

        # Initialize Gemini STT (no fallback)
        self.stt = SpeechToText()
    def get_current_stage(self, question_number):
        """Determine interview stage based on question number"""
        for stage, (start, end) in self.question_stages.items():
            if start <= question_number <= end:
                return stage
        return 'closing'

    def generate_question(self, question_number, previous_response=None, interview_context=None):
        """Generate next interview question using DeepSeek"""
        stage = self.get_current_stage(question_number)
        system_prompt = self._get_system_prompt(stage, question_number)
        user_prompt = self._build_user_prompt(stage, question_number, previous_response, interview_context)

        try:
            response = self._call_deepseek_api(user_prompt, system_prompt)
            question_text = response.strip()

            # Generate TTS audio
            audio_base64 = self.text_to_speech_gtts(question_text)

            return {
                'success': True,
                'question': question_text,
                'audio_base64': audio_base64,
                'stage': stage,
                'question_number': question_number,
                'has_audio': audio_base64 is not None
            }
        except Exception as e:
            logger.error(f"Error generating question {question_number}: {e}")
            # NO FALLBACK - just return error
            return {
                'success': False,
                'error': str(e),
                'question': None,
                'audio_base64': None,
                'stage': stage,
                'question_number': question_number,
                'has_audio': False
            }

    def process_voice_response_with_gemini(self, audio_file_path):
        """Process voice response using Gemini STT"""
        try:
            if isinstance(audio_file_path, bytes):
                audio_data = audio_file_path
            else:
                with open(audio_file_path, 'rb') as f:
                    audio_data = f.read()

            # Use Gemini STT class for conversion
            transcription = self.stt.convert_audio_to_text(audio_data)

            if not transcription:
                return {
                    'success': False,
                    'error': 'Could not transcribe audio. Please speak clearly.',
                    'transcription': None
                }

            return {
                'success': True,
                'transcription': transcription,
                'confidence': 1.0  # Gemini doesn't provide confidence scores
            }

        except Exception as e:
            logger.error(f"Error processing voice response: {e}")
            return {
                'success': False,
                'error': str(e),
                'transcription': None
            }

    def text_to_speech_gtts(self, text, voice_style='default'):
        """Convert text to speech with different voice options."""
        try:
            _ensure_directory(TTS_CACHE_DIR)
            cache_key = hashlib.sha256(f"{voice_style}:{text}".encode('utf-8')).hexdigest()
            cache_path = os.path.join(TTS_CACHE_DIR, f"{cache_key}.mp3")

            if os.path.exists(cache_path):
                with open(cache_path, 'rb') as cached_audio:
                    return base64.b64encode(cached_audio.read()).decode('utf-8')

            logger.info(f"Generating TTS for question with voice: {voice_style}")

            # Generate audio using gTTS with different voice options
            from gtts import gTTS

            # Voice configuration
            voice_configs = {
                'default': {'lang': 'en', 'tld': 'com', 'slow': False},
                'uk': {'lang': 'en', 'tld': 'co.uk', 'slow': False},  # British accent
                'au': {'lang': 'en', 'tld': 'com.au', 'slow': False},  # Australian accent
                'ca': {'lang': 'en', 'tld': 'ca', 'slow': False},     # Canadian accent
                'slow': {'lang': 'en', 'tld': 'com', 'slow': True},   # Slower pace
            }

            config = voice_configs.get(voice_style, voice_configs['default'])

            tts = gTTS(text=text, **config)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_content = audio_buffer.getvalue()

            with open(cache_path, 'wb') as cached_audio:
                cached_audio.write(audio_content)

            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
            logger.info(f"TTS generated successfully with {voice_style} voice")
            return audio_base64

        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None

    # Keep all your existing methods: _get_system_prompt, _build_user_prompt,
    # _call_deepseek_api, _get_fallback_question
    def _get_system_prompt(self, stage, question_number):
        """Get system prompt based on interview stage"""
        base_prompt = """You are a professional technical interviewer conducting a comprehensive interview for a data science/machine learning role. Generate ONE clear, specific question that naturally follows from the conversation context."""

        stage_prompts = {
            'intro': f"{base_prompt} Focus on introduction and background. This is question {question_number} of the introduction phase.",
            'projects': f"{base_prompt} Focus on past projects and practical experience. Ask about specific projects they've worked on.",
            'python': f"{base_prompt} Focus on Python programming skills, libraries, and coding practices.",
            'statistics': f"{base_prompt} Focus on statistical concepts, methods, and practical applications.",
            'ml': f"{base_prompt} Focus on machine learning algorithms, model selection, and real-world ML challenges.",
            'closing': f"{base_prompt} This is the final question. Ask about questions they have or final thoughts."
        }

        return stage_prompts.get(stage, base_prompt)

    def _build_user_prompt(self, stage, question_number, previous_response, interview_context):
        """Build user prompt with context - FIXED VERSION"""
        if question_number == 1:
            return "Generate a warm, professional opening question to start the technical interview. Ask the candidate to introduce themselves and share their background in data science or related fields. Return ONLY the question text."

        context_text = ""
        if previous_response:
            context_text = f"Candidate's previous response: \"{previous_response}\"\n\n"

        stage_instructions = {
            'intro': "Generate a follow-up introduction question. Ask about their experience level, education, or what interests them about data science. Keep it conversational.",
            'projects': "Ask about a specific project they've worked on. Focus on their role, technologies used, challenges faced, or outcomes achieved.",
            'python': "Ask a Python programming question. Topics: pandas, numpy, data manipulation, visualization libraries, or coding practices.",
            'statistics': "Ask about statistical concepts: hypothesis testing, probability, distributions, A/B testing, or statistical analysis methods.",
            'ml': "Ask about machine learning: algorithm selection, model evaluation, overfitting, feature engineering, or real-world ML challenges.",
            'closing': "Ask if they have questions about the role or company, or invite them to share anything else they'd like to highlight."
        }

        instruction = stage_instructions.get(stage, "Generate the next logical interview question.")

        return f"{context_text}Based on the conversation flow, {instruction}\n\nIMPORTANT: Return ONLY the question text. Do not include any explanations, context, or additional text. Just the question."
    def _call_deepseek_api(self, user_prompt, system_prompt):
        """Call DeepSeek API via OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.7,
            "top_p": 0.9
        }

        response = HTTP_SESSION.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")

    def _get_fallback_question(self, stage, question_number):
        """Fallback questions if API fails"""
        fallback_questions = {
            'intro': [
                "Can you tell me about your background and how you got interested in data science?",
                "What programming languages and tools do you have experience with?",
                "What type of role are you looking for and what interests you about data science?"
            ],
            'projects': [
                "Can you describe a recent data science project you've worked on?",
                "Tell me about a challenging problem you solved using data analysis.",
                "What was the most interesting insight you discovered from a dataset?"
            ],
            'python': [
                "How comfortable are you with Python libraries like pandas and numpy?",
                "Can you explain the difference between a list and a dictionary in Python?",
                "What's your approach to debugging Python code when it's not working as expected?"
            ],
            'statistics': [
                "Can you explain what a p-value represents in statistical testing?",
                "How would you determine if a dataset follows a normal distribution?",
                "What's the difference between correlation and causation?"
            ],
            'ml': [
                "How do you approach the problem of overfitting in machine learning models?",
                "Can you explain the difference between supervised and unsupervised learning?",
                "What factors do you consider when choosing between different machine learning algorithms?"
            ],
            'closing': [
                "Do you have any questions about the role or our team?",
                "Is there anything else about your background or experience you'd like to share?",
                "What questions do you have about working here?"
            ]
        }

        questions = fallback_questions.get(stage, ["Thank you for your time today."])
        index = (question_number - 1) % len(questions)
        return questions[index]


# ADD THESE NEW VIEWS to your interview_system/views.py file
# (Add at the END of your views.py file, don't replace existing views)

@csrf_exempt
@require_http_methods(["POST"])
def start_voice_interview(request):
    """Initialize voice interview session using CSV questions only with TTS"""

    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({'error': 'No active interview found'}, status=404)

        # Create or get voice interview session
        voice_session, created = VoiceInterviewSession.objects.get_or_create(
            interview=interview,
            defaults={
                'current_question_number': 1,
                'current_stage': 'technical',
                'interview_context': [],
                'session_data': {
                    'started_at': timezone.now().isoformat(),
                    'total_questions_asked': 0
                }
            }
        )

        # Start session tracking
        if created or voice_session.session_status == 'not_started':
            voice_session.start_session()
            interview.voice_interview_started = True
            interview.save(update_fields=['voice_interview_started'])

        # =========================
        # FETCH FIRST QUESTION FROM CSV
        # =========================
        question_obj = get_random_question(interview)

        if not question_obj:
            return JsonResponse({
                'success': False,
                'error': 'No questions available'
            })

        # Update session with first question
        voice_session.current_question_number = 1
        voice_session.current_stage = 'technical'
        voice_session.session_data['current_question'] = question_obj.question_text
        voice_session.session_data['current_question_id'] = str(question_obj.id)
        voice_session.save()

        # =========================
        # 🔥 GENERATE TTS FOR FIRST QUESTION
        # =========================
        agent = VoiceInterviewAgent()
        audio_payload = _build_question_audio_payload(agent, question_obj.question_text)

        return JsonResponse({
            'success': True,
            'question': question_obj.question_text,
            'question_id': str(question_obj.id),
            'question_number': 1,
            'stage': voice_session.current_stage,
            'session_id': voice_session.id,
            'total_questions': interview.total_questions,
            'has_audio': audio_payload['has_audio'],
            'audio_base64': audio_payload['audio_base64'],
        })

    except Exception as e:
        logger.error(f"Error starting voice interview: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
        # ============================
        # GET FIRST QUESTION FROM CSV
        # ============================

        question_obj = get_random_question(interview)

        if not question_obj:
            return JsonResponse({
                'success': False,
                'error': 'No questions available in database'
            }, status=400)

        first_question = {
            'question': question_obj.question_text,
            'question_id': str(question_obj.id),
            'stage': 'technical',
            'has_audio': False,
            'audio_base64': None
        }

        # Save question in session
        voice_session.session_data['current_question'] = first_question['question']
        voice_session.session_data['current_question_id'] = first_question['question_id']
        voice_session.current_question_number = 1
        voice_session.save()

        return JsonResponse({
            'success': True,
            'question': first_question['question'],
            'question_id': first_question['question_id'],
            'question_number': 1,
            'stage': first_question['stage'],
            'session_id': voice_session.id,
            'total_questions': interview.total_questions,
            'has_audio': False,
            'audio_base64': None,
        })

    except Exception as e:
        logger.error(f"Error starting voice interview: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to start voice interview'
        }, status=500)


# Replace your existing process_voice_response view with this:
@csrf_exempt
@require_http_methods(["POST"])
def process_voice_response(request):
    """Process voice response with low-latency local persistence and cached TTS."""

    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        audio_file = request.FILES.get('audio')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)

        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({'error': 'No active interview found'}, status=404)

        voice_session = VoiceInterviewSession.objects.filter(interview=interview).first()
        if not voice_session:
            return JsonResponse({'error': 'Voice session not found'}, status=404)

        audio_bytes = b''.join(audio_file.chunks())
        agent = VoiceInterviewAgent()

        stt_result = agent.process_voice_response_with_gemini(audio_bytes)
        if not stt_result['success']:
            return JsonResponse({
                'success': False,
                'error': stt_result['error']
            })

        transcription = stt_result['transcription']
        current_question_number = voice_session.current_question_number
        current_question_id = voice_session.session_data.get('current_question_id')

        if not current_question_id:
            return JsonResponse({'success': False, 'error': 'Current question is missing from session'}, status=400)

        try:
            current_question = Question.objects.get(id=current_question_id)
        except Question.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Current question no longer exists'}, status=404)

        local_audio_path = _save_audio_locally(interview, current_question_number, audio_bytes)
        response_record = InterviewResponse.objects.create(
            interview=interview,
            question=current_question,
            audio_file_path=local_audio_path,
            local_file_path=local_audio_path
        )
        _append_interview_context(voice_session, current_question, transcription)

        threading.Thread(
            target=_upload_audio_to_hdfs_in_background,
            args=(response_record.id, interview.id, current_question_number, local_audio_path),
            daemon=True,
        ).start()

        voice_session.record_question_answered(audio_saved=True)

        if current_question_number >= interview.total_questions:
            voice_session.complete_session(reason='completed')

            interview.voice_interview_completed = True
            interview.completion_reason = 'all_questions_answered'
            interview.questions_answered = interview.total_questions
            interview.completion_percentage = 100
            interview.processing_status = 'processing'
            interview.save()

            threading.Thread(
                target=_run_final_interview_analysis,
                args=(interview.id,),
                daemon=True,
            ).start()

            return JsonResponse({
                'success': True,
                'interview_complete': True,
                'transcription': transcription
            })

        next_question_number = current_question_number + 1
        question_obj = get_random_question(interview, excluded_question_ids={current_question.id})

        if not question_obj:
            return JsonResponse({
                'success': False,
                'error': 'No more questions available'
            })

        voice_session.current_question_number = next_question_number
        voice_session.current_stage = 'technical'
        voice_session.session_data['current_question'] = question_obj.question_text
        voice_session.session_data['current_question_id'] = str(question_obj.id)
        voice_session.save()

        audio_payload = _build_question_audio_payload(agent, question_obj.question_text)

        return JsonResponse({
            'success': True,
            'transcription': transcription,
            'next_question': question_obj.question_text,
            'question_id': str(question_obj.id),
            'question_number': next_question_number,
            'progress_percentage': int(
                (next_question_number / interview.total_questions) * 100
            ),
            'interview_complete': False,
            'audio_base64': audio_payload['audio_base64'],
            'has_audio': audio_payload['has_audio']
        })

    except Exception as e:
        logger.error(f"Error processing voice response: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
@require_http_methods(["GET"])
def get_voice_interview_status(request, interview_id):
    """Get voice interview status"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)

        if not (request.user == interview.student or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)

        voice_session = VoiceInterviewSession.objects.filter(interview=interview).first()

        if not voice_session:
            return JsonResponse({
                'voice_interview_active': False,
                'interview_id': interview_id
            })

        return JsonResponse({
            'voice_interview_active': True,
            'interview_id': interview_id,
            'current_question_number': voice_session.current_question_number,
            'current_stage': voice_session.current_stage,
            'total_questions': VOICE_INTERVIEW_CONFIG['MAX_QUESTIONS'],
            'progress_percentage': int((voice_session.current_question_number / VOICE_INTERVIEW_CONFIG['MAX_QUESTIONS']) * 100),
            'session_data': voice_session.session_data
        })

    except Exception as e:
        logger.error(f"Error getting voice interview status: {e}")
        return JsonResponse({'error': 'Failed to get status'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def end_voice_interview(request):
    """End voice interview session"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)

        interview = Interview.objects.filter(
            student=request.user,
            status='in_progress'
        ).first()

        if not interview:
            return JsonResponse({'error': 'No active interview found'}, status=404)

        voice_session = VoiceInterviewSession.objects.filter(interview=interview).first()
        questions_completed = 0
        if voice_session:
            questions_completed = voice_session.current_question_number
            voice_session.session_data['ended_at'] = timezone.now().isoformat()
            voice_session.session_data['ended_by_user'] = True
            voice_session.save()
            
            # Use new completion tracking - mark as user ended early
            voice_session.complete_session(reason='user_ended')
            
            # Update parent interview with completion info
            interview.questions_answered = questions_completed
            interview.completion_percentage = (questions_completed / interview.total_questions) * 100
            if questions_completed < interview.total_questions:
                interview.completion_reason = 'user_ended_early'
            interview.save(update_fields=['questions_answered', 'completion_percentage', 'completion_reason'])

        return JsonResponse({
            'success': True,
            'message': 'Voice interview ended successfully',
            'questions_completed': questions_completed,
            'completion_percentage': (questions_completed / 15) * 100 if questions_completed else 0
        })

    except Exception as e:
        logger.error(f"Error ending voice interview: {e}")
        return JsonResponse({'error': 'Failed to end voice interview'}, status=500)
    from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4

def add_watermark(canvas_obj, doc):
    canvas_obj.saveState()

    width, height = A4

    watermark_color = Color(0.2, 0.4, 0.8, alpha=0.45)
    canvas_obj.setFillColor(watermark_color)

    canvas_obj.setFont("Helvetica-Bold", 80)

    canvas_obj.translate(width / 2, height / 2)
    canvas_obj.rotate(45)

    canvas_obj.drawCentredString(0, 0, "STUDENT REPORT")

    canvas_obj.restoreState()
@login_required
def download_student_report(request, interview_id):
    """
    Generate and download student interview report as PDF
    """

    interview = get_object_or_404(Interview, id=interview_id, student=request.user)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Interview_Report_{interview.id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    voice_session = VoiceInterviewSession.objects.filter(interview=interview).first()
    analysis_summary = {}
    if voice_session and isinstance(voice_session.session_data, dict):
        analysis_summary = voice_session.session_data.get('analysis_summary', {})

    # Title
    title_style = styles['Heading1']
    title_style.alignment = 1
    elements.append(Paragraph("STUDENT REPORT", title_style))
    elements.append(Spacer(1, 20))

    # Student Info Table
    student_profile = getattr(request.user, 'student_profile', None)

    student_data = [
        ['Name:', request.user.get_full_name()],
        ['Date of Birth:', getattr(student_profile, 'date_of_birth', 'Not Provided')],
        ['Course:', getattr(student_profile, 'course', 'Not Provided')],
        ['Interview Applied For:', 'Software Developer'],
    ]

    table = Table(student_data, colWidths=[170, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 30))

    # Best At
    elements.append(Paragraph("<b>You Are Best At:</b>", styles['Heading3']))
    elements.append(Spacer(1, 10))

    best_points = analysis_summary.get('strengths') or [
        "Technical score available after interview analysis",
        "Communication score available after interview analysis",
        "Confidence score available after interview analysis"
    ]

    elements.append(ListFlowable(
        [ListItem(Paragraph(p, styles['Normal'])) for p in best_points],
        bulletType='bullet'
    ))

    elements.append(Spacer(1, 30))

    # Needs Improvement
    elements.append(Paragraph("<b>Needs Improvement:</b>", styles['Heading3']))
    elements.append(Spacer(1, 10))

    improve_points = analysis_summary.get('improvements') or [
        "Awaiting automated improvement suggestions",
        "Awaiting automated improvement suggestions",
        "Awaiting automated improvement suggestions"
    ]

    elements.append(ListFlowable(
        [ListItem(Paragraph(p, styles['Normal'])) for p in improve_points],
        bulletType='bullet'
    ))

    elements.append(Spacer(1, 30))

    # Scores Table
    elements.append(Paragraph("<b>Performance Scores:</b>", styles['Heading3']))
    elements.append(Spacer(1, 10))

    score_data = [
        ['Section', 'Score'],
        ['Technical Skills', f'{interview.technical_score or 0:.1f} / 100'],
        ['Communication Skills', f'{interview.communication_score or 0:.1f} / 100'],
        ['Confidence', f'{interview.confidence_score or 0:.1f} / 100'],
        ['Overall Score', f'{interview.overall_score or 0:.1f} / 100'],
    ]

    score_table = Table(score_data, colWidths=[250, 150])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.darkblue),
        ('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('GRID', (0,0), (-1,-1), 1, colors.grey),
        ('ALIGN',(1,1),(-1,-1),'CENTER'),
    ]))

    elements.append(score_table)
    elements.append(Spacer(1, 40))

    if analysis_summary.get('summary'):
        elements.append(Paragraph("<b>Evaluator Summary:</b>", styles['Heading3']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(analysis_summary['summary'], styles['Normal']))
        elements.append(Spacer(1, 20))

    elements.append(Paragraph("Thank You", styles['Normal']))

    doc.build(elements, onFirstPage=add_watermark, onLaterPages=add_watermark)


    return response
# ============================================
# STUDENT RESULTS PAGE VIEW
# ============================================

@login_required
def interview_results(request, interview_id):
    """
    Display interview results page
    - Student can see their own
    - Admin can see any
    """

    if request.user.is_staff:
        interview = get_object_or_404(Interview, id=interview_id)
    else:
        interview = get_object_or_404(
            Interview,
            id=interview_id,
            student=request.user
        )

    return render(request, 'interview_system/interview_results.html', {
        'interview': interview
    })
from django.views.decorators.http import require_POST

@staff_member_required
@require_POST
def delete_interview(request, interview_id):
    """
    Delete an interview (Admin only)
    """
    try:
        interview = get_object_or_404(Interview, id=interview_id)

        interview.delete()

        return JsonResponse({
            'success': True,
            'message': 'Interview deleted successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting interview {interview_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to delete interview'
        }, status=500)
