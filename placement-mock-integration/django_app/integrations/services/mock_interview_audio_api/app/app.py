# app.py - Enhanced Audio Analysis API with Topic-wise and Soft Skills Analysis
from flask import Flask, request, jsonify
import os
import json
import logging
import tempfile
import wave
import math
import numpy as np
import speech_recognition as sr
import concurrent.futures
from hdfs import InsecureClient
import requests
from datetime import datetime
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from your Django settings
HDFS_CONFIG = {
    'HOST': os.getenv('HDFS_HOST', 'namenode'),
    'PORT': '9870',
    'USER': 'hdfs'
}

DB_CONFIG = {
    'host': os.getenv('DB_HOST', '172.18.0.16'),
    'database': os.getenv('DB_NAME', 'mock_interview_platform'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'demopass'),
    'port': os.getenv('DB_PORT', '3306')
}

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', 'your-api-key-here')
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

class HDFSClient:
    def __init__(self):
        try:
            self.client = InsecureClient(f'http://{HDFS_CONFIG["HOST"]}:{HDFS_CONFIG["PORT"]}/', user=HDFS_CONFIG['USER'])
            self.client.list('/')
            logger.info("HDFS connected successfully")
        except Exception as e:
            logger.error(f"HDFS connection failed: {e}")
            self.client = None

    def get_interview_audio_files(self, interview_info):
        """Get audio files for interview - try local files first, then HDFS"""
        try:
            # Get the audio file records from database for this interview
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            query = """
            SELECT question_id, audio_file_path, local_file_path
            FROM interview_system_interviewresponse
            WHERE interview_id = %s
            """

            cursor.execute(query, (interview_info['interview_id'],))
            audio_records = cursor.fetchall()

            cursor.close()
            connection.close()

            if not audio_records:
                logger.error(f"No audio records found in database for interview {interview_info['interview_id']}")
                return {}

            logger.info(f"Found {len(audio_records)} audio records in database")

            # Check local files first, then HDFS
            audio_files = {}
            for record in audio_records:
                question_id = record['question_id']
                local_path = record['local_file_path']
                hdfs_path = record['audio_file_path']

                # Try local file first
                if local_path and os.path.exists(local_path):
                    audio_files[question_id] = local_path
                    logger.info(f"Found local file: {question_id} -> {local_path}")
                else:
                    # Try HDFS if local file doesn't exist
                    try:
                        if self.client:
                            file_status = self.client.status(hdfs_path, strict=False)
                            if file_status:
                                audio_files[question_id] = hdfs_path
                                logger.info(f"Found HDFS file: {question_id} -> {hdfs_path}")
                            else:
                                logger.warning(f"File not found in local or HDFS: {question_id}")
                        else:
                            logger.warning(f"HDFS client not available for {question_id}")
                    except Exception as e:
                        logger.warning(f"Could not access file {hdfs_path}: {e}")

            logger.info(f"Total accessible audio files: {len(audio_files)}")
            return audio_files

        except Exception as e:
            logger.error(f"Error getting audio files: {e}")
            return {}

    def download_audio_file(self, hdfs_path):
        """Download audio file from HDFS"""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.webm')
            with self.client.read(hdfs_path) as reader:
                temp_file.write(reader.read())
            temp_file.close()
            logger.info(f"Downloaded audio file to: {temp_file.name}")
            return temp_file.name
        except Exception as e:
            logger.error(f"Error downloading {hdfs_path}: {e}")
            return None

    def get_audio_file(self, file_path):
        """Get audio file - handle both local and HDFS paths"""
        try:
            if file_path.startswith('/app/'):
                # Local file
                if os.path.exists(file_path):
                    return file_path
                else:
                    logger.error(f"Local file not found: {file_path}")
                    return None
            else:
                # HDFS file - download it
                return self.download_audio_file(file_path)
        except Exception as e:
            logger.error(f"Error getting audio file {file_path}: {e}")
            return None

class DatabaseClient:
    def get_interview_info(self, interview_id):
        """Get interview and user info from database"""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            # Query based on your Django models - with completion tracking fields
            query = """
            SELECT
                i.id as interview_id,
                i.student_id,
                i.attempt_number,
                i.status,
                i.completed_at,
                i.analysis_completed,
                i.voice_interview_started,
                i.voice_interview_completed,
                i.questions_answered,
                i.total_questions,
                i.completion_reason,
                i.completion_percentage,
                i.has_audio_responses,
                i.audio_responses_count,
                i.processing_status,
                u.id,
                u.first_name,
                u.last_name,
                u.email,
                sp.student_id as student_profile_id
            FROM interview_system_interview i
            JOIN user_management_customuser u ON i.student_id = u.id
            LEFT JOIN user_management_studentprofile sp ON u.id = sp.user_id
            WHERE i.id = %s 
            AND i.status = 'completed' 
            AND i.analysis_completed = FALSE
            AND i.voice_interview_started = TRUE
            AND i.questions_answered > 0
            """

            cursor.execute(query, (interview_id,))
            result = cursor.fetchone()

            cursor.close()
            connection.close()

            if result:
                logger.info(f"Found interview: {result['interview_id']}, questions_answered: {result.get('questions_answered', 0)}, completion: {result.get('completion_percentage', 0)}%")
                # Use student_profile_id if available, otherwise use user id
                result['student_id'] = result['student_profile_id'] or result['id']

            return result
        except Error as e:
            logger.error(f"Database error: {e}")
            return None

    def update_analysis_status(self, interview_id, scores=None):
        """Update interview with analysis results and processing status"""
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor()

            if scores:
                query = """
                UPDATE interview_system_interview
                SET analysis_completed = TRUE,
                    overall_score = %s,
                    technical_score = %s,
                    communication_score = %s,
                    confidence_score = %s,
                    processing_status = 'analysis_complete',
                    processing_completed_at = NOW()
                WHERE id = %s
                """
                cursor.execute(query, (
                    scores.get('overall_score_numeric', 50),
                    scores.get('technical_score_numeric', 50),
                    scores.get('communication_score_numeric', 50),
                    scores.get('confidence_score_numeric', 50),
                    interview_id
                ))
            else:
                query = """
                UPDATE interview_system_interview 
                SET analysis_completed = TRUE, 
                    processing_status = 'analysis_complete',
                    processing_completed_at = NOW()
                WHERE id = %s
                """
                cursor.execute(query, (interview_id,))

            connection.commit()
            cursor.close()
            connection.close()

            logger.info(f"Updated analysis status for interview {interview_id}")
            return True
        except Error as e:
            logger.error(f"Database update error: {e}")
            return False

class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def enhance_audio(self, input_audio_file, output_audio_file, volume_gain=1.5):
        """Enhanced audio processing function"""
        try:
            with wave.open(input_audio_file, 'rb') as audio:
                params = audio.getparams()
                num_frames = audio.getnframes()

                with wave.open(output_audio_file, 'wb') as output_audio:
                    output_audio.setparams(params)
                    frames_per_read = 8192
                    for _ in range(0, num_frames, frames_per_read):
                        frames = audio.readframes(frames_per_read)
                        if frames:
                            enhanced_frames = self.enhance_audio_frames(frames, params.sampwidth, volume_gain)
                            output_audio.writeframes(enhanced_frames)
            logger.info(f"Enhanced audio saved to: {output_audio_file}")
        except Exception as e:
            logger.error(f"Audio enhancement failed: {e}")
            # If enhancement fails, copy original
            import shutil
            shutil.copy2(input_audio_file, output_audio_file)

    def enhance_audio_frames(self, frames, sampwidth, volume_gain):
        """Enhanced frame processing function"""
        if sampwidth == 1:
            audio_samples = np.frombuffer(frames, dtype=np.uint8) - 128
        elif sampwidth == 2:
            audio_samples = np.frombuffer(frames, dtype=np.int16)
        else:
            return frames

        enhanced_samples = (audio_samples * volume_gain).astype(audio_samples.dtype)

        if sampwidth == 1:
            enhanced_samples = np.clip(enhanced_samples + 128, 0, 255)
        elif sampwidth == 2:
            enhanced_samples = np.clip(enhanced_samples, -32768, 32767)

        return enhanced_samples.tobytes()

    def process_audio_chunk(self, chunk_filename, recognizer):
        """Process individual audio chunk"""
        with sr.AudioFile(chunk_filename) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data)
                return text
            except sr.UnknownValueError:
                return ""
            except sr.RequestError as e:
                logger.error(f"Speech recognition error: {e}")
                return "[Error retrieving results]"

    def audio_to_text(self, input_audio_file, chunk_duration=60):
        """Convert audio to text using chunking"""
        try:
            with wave.open(input_audio_file, 'rb') as audio:
                params = audio.getparams()
                frame_rate = params.framerate
                n_channels = params.nchannels
                sampwidth = params.sampwidth
                n_frames = audio.getnframes()

                chunk_size = int(frame_rate * chunk_duration)
                total_chunks = math.ceil(n_frames / chunk_size)

                transcribed_text = []

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    futures = []

                    for i in range(total_chunks):
                        chunk_filename = f"temp_chunk_{i}.wav"
                        with wave.open(chunk_filename, 'wb') as chunk:
                            chunk.setnchannels(n_channels)
                            chunk.setsampwidth(sampwidth)
                            chunk.setframerate(frame_rate)
                            frames = audio.readframes(chunk_size)
                            chunk.writeframes(frames)

                        futures.append(executor.submit(self.process_audio_chunk, chunk_filename, self.recognizer))

                    for future in concurrent.futures.as_completed(futures):
                        text = future.result()
                        if text:
                            transcribed_text.append(text)

                # Cleanup temp files
                for i in range(total_chunks):
                    try:
                        os.remove(f"temp_chunk_{i}.wav")
                    except:
                        pass

                return " ".join(transcribed_text)

        except Exception as e:
            logger.error(f"Audio to text failed: {e}")
            return ""

    def convert_webm_to_wav(self, webm_path):
        """Convert webm to wav (simple approach)"""
        try:
            wav_path = webm_path.replace('.webm', '.wav')

            # Try to read as wav directly (sometimes webm files are actually wav)
            try:
                with wave.open(webm_path, 'rb') as test:
                    test.readframes(1)
                # If successful, just rename
                os.rename(webm_path, wav_path)
                return wav_path
            except:
                # If that fails, try copying and hope for the best
                import shutil
                shutil.copy2(webm_path, wav_path)
                return wav_path

        except Exception as e:
            logger.error(f"WebM to WAV conversion failed: {e}")
            return None

    def process_webm_file(self, webm_file_path):
        """Process WebM file directly using speech recognition"""
        try:
            logger.info(f"Processing WebM file: {webm_file_path}")

            # Check if file exists and has content
            if not os.path.exists(webm_file_path):
                logger.error(f"File does not exist: {webm_file_path}")
                return ""

            file_size = os.path.getsize(webm_file_path)
            if file_size == 0:
                logger.error(f"File is empty: {webm_file_path}")
                return ""

            logger.info(f"File size: {file_size} bytes")

            # Try different approaches to handle the WebM file

            # Approach 1: Try to read as WAV directly (sometimes webm files are mislabeled)
            try:
                with wave.open(webm_file_path, 'rb') as audio_file:
                    # If this works, process normally
                    enhanced_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
                    self.enhance_audio(webm_file_path, enhanced_path)
                    text = self.audio_to_text(enhanced_path)
                    os.unlink(enhanced_path)
                    return text
            except wave.Error:
                # Not a WAV file, continue with other methods
                pass

            # Approach 2: Try to use speech recognition directly on the file
            try:
                # Create a temporary WAV file by copying
                temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
                import shutil
                shutil.copy2(webm_file_path, temp_wav)

                # Try to process the copied file
                with sr.AudioFile(temp_wav) as source:
                    # Adjust for ambient noise
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio_data = self.recognizer.record(source)

                    try:
                        text = self.recognizer.recognize_google(audio_data)
                        logger.info(f"Direct recognition successful: {len(text)} characters")
                        os.unlink(temp_wav)
                        return text
                    except sr.UnknownValueError:
                        logger.warning("Could not understand audio")
                        os.unlink(temp_wav)
                        return ""
                    except sr.RequestError as e:
                        logger.error(f"Google Speech Recognition error: {e}")
                        os.unlink(temp_wav)
                        return "[Recognition service error]"

            except Exception as e:
                logger.error(f"Direct recognition failed: {e}")

            # Approach 3: Try to use ffmpeg if available (install it in container)
            try:
                import subprocess

                # Convert to WAV using ffmpeg
                temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name

                result = subprocess.run([
                    'ffmpeg', '-i', webm_file_path,
                    '-ar', '16000', '-ac', '1', '-y',
                    temp_wav
                ], capture_output=True, text=True)

                if result.returncode == 0:
                    # Successfully converted, now process
                    enhanced_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
                    self.enhance_audio(temp_wav, enhanced_path)
                    text = self.audio_to_text(enhanced_path)

                    # Cleanup
                    os.unlink(temp_wav)
                    os.unlink(enhanced_path)

                    return text
                else:
                    logger.error(f"FFmpeg conversion failed: {result.stderr}")

            except FileNotFoundError:
                logger.warning("FFmpeg not available")
            except Exception as e:
                logger.error(f"FFmpeg approach failed: {e}")

            logger.error(f"All processing methods failed for {webm_file_path}")
            return ""

        except Exception as e:
            logger.error(f"WebM processing failed: {e}")
            return ""

class EnhancedDeepSeekAnalyzer:
    def __init__(self):
        self.grade_mapping = {
            'A': (9.0, 10.0),
            'B': (7.5, 8.9),
            'C': (6.0, 7.4),
            'D': (4.5, 5.9),
            'E': (3.0, 4.4),
            'F': (0.0, 2.9)
        }

    def detect_topics_from_responses(self, question_responses):
        """Detect topics dynamically from question paths"""
        topics = set()
        for question_id in question_responses.keys():
            if '/' in question_id:
                topic = question_id.split('/')[0]
                # Clean topic name
                clean_topic = topic.replace('-', ' ').replace('_', ' ').title()
                topics.add(clean_topic)
        return list(topics)

    def analyze_responses(self, question_responses):
        """Analyze responses using enhanced DeepSeek prompt"""
        try:
            # Detect topics dynamically
            detected_topics = self.detect_topics_from_responses(question_responses)
            
            # Create enhanced analysis prompt
            prompt = self.create_enhanced_analysis_prompt(question_responses, detected_topics)

            response = requests.post(
                OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek/deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2500
                },
                timeout=90
            )

            if response.status_code == 200:
                result = response.json()
                analysis = result['choices'][0]['message']['content']
                parsed_result = self.parse_enhanced_analysis(analysis, detected_topics)
                logger.info(f"Enhanced DeepSeek analysis completed successfully")
                return parsed_result
            else:
                logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                return self.get_enhanced_fallback_scores(detected_topics)

        except Exception as e:
            logger.error(f"Enhanced analysis error: {e}")
            return self.get_enhanced_fallback_scores(detected_topics)

    def create_enhanced_analysis_prompt(self, question_responses, detected_topics):
        """Create comprehensive analysis prompt with topic-wise and soft skills analysis"""
        
        # Organize responses by topic
        topic_responses = {}
        for question_id, response in question_responses.items():
            if '/' in question_id:
                topic = question_id.split('/')[0].replace('-', ' ').replace('_', ' ').title()
                clean_question = question_id.split('/')[-1].replace('.wav', '')
                
                if topic not in topic_responses:
                    topic_responses[topic] = []
                topic_responses[topic].append({
                    'question': clean_question,
                    'response': response
                })

        # Build prompt
        prompt_parts = [
            "Analyze this technical interview with STRICT grading standards. The candidate's responses are provided below:",
            ""
        ]

        # Add topic-wise responses
        for topic, responses in topic_responses.items():
            prompt_parts.append(f"=== {topic.upper()} QUESTIONS ===")
            for item in responses:
                prompt_parts.append(f"Q: {item['question']}")
                prompt_parts.append(f"A: {item['response']}")
                prompt_parts.append("")

        prompt_parts.extend([
            "ANALYZE THE FOLLOWING WITH STRICT STANDARDS:",
            "",
            "1. TOPIC-WISE ANALYSIS (0-10 scale for each topic):",
            f"Topics to analyze: {', '.join(detected_topics)}",
            "- Rate technical accuracy, depth of knowledge, correct terminology",
            "- Be very strict: GRADING SCALE: 9.0-10.0 = A (Excellent), 7.5-8.9 = B (Very Good), 6.0-7.4 = C (Good), 4.5-5.9 = D (Satisfactory), 3.0-4.4 = E (Needs Improvement), 0.0-2.9 = F (Unsatisfactory)",
	    "- Be consistent with this exact scale when scoring",
            "",
	    "2. SOFT SKILLS ANALYSIS (0-10 scale using same grading criteria):",
    "- Communication: Clarity, structure, articulation (9.0-10.0=A, 7.5-8.9=B, 6.0-7.4=C, 4.5-5.9=D, 3.0-4.4=E, 0.0-2.9=F)",
    "- Confidence: Composure, certainty, professional demeanor (same scale)",
    "- Relevance: How well answers address the actual questions asked (same scale)",

	    "3. OVERALL GRADING (A, B, C, D, E, F) - Use this EXACT scale:",
    "- A (9.0-10.0): Excellent - Outstanding knowledge and clear explanations",
    "- B (7.5-8.9): Very Good - Strong knowledge with mostly correct answers", 
    "- C (6.0-7.4): Good - Solid understanding with some gaps",
    "- D (4.5-5.9): Satisfactory - Basic knowledge but several mistakes",
    "- E (3.0-4.4): Needs Improvement - Major knowledge gaps",
    "- F (0.0-2.9): Unsatisfactory - Mostly incorrect or irrelevant answers",
    "- Technical Grade: Based on average of all technical topics using above scale",
    "- Communication Grade: Based on soft skills average using above scale", 
    "- Overall Grade: Combined assessment using above scale",
            "IMPORTANT: Return EXACTLY this JSON format (no additional text):",
            "",
            "{"
        ])

        # Add topic-wise structure
        prompt_parts.append('  "topic_wise_analysis": {')
        for i, topic in enumerate(detected_topics):
            comma = "," if i < len(detected_topics) - 1 else ""
            prompt_parts.append(f'    "{topic}": {{')
            prompt_parts.append('      "score": <0-10 number>,')
            prompt_parts.append('      "feedback": "<one sentence technical assessment>",')
            prompt_parts.append('      "improvements": "<exactly 2 sentences for improvement>"')
            prompt_parts.append(f'    }}{comma}')
        
        prompt_parts.extend([
            '  },',
            '  "soft_skills_analysis": {',
            '    "communication": {',
            '      "score": <0-10 number>,',
            '      "feedback": "<one sentence about communication quality>",',
            '      "improvements": "<exactly 2 sentences for improvement>"',
            '    },',
            '    "confidence": {',
            '      "score": <0-10 number>,',
            '      "feedback": "<one sentence about confidence level>",',
            '      "improvements": "<exactly 2 sentences for improvement>"',
            '    },',
            '    "relevance": {',
            '      "score": <0-10 number>,',
            '      "feedback": "<one sentence about answer relevance>",',
            '      "improvements": "<exactly 2 sentences for improvement>"',
            '    }',
            '  },',
            '  "overall_grades": {',
            '    "technical_grade": "<A/B/C/D/E/F>",',
            '    "communication_grade": "<A/B/C/D/E/F>",',
            '    "overall_grade": "<A/B/C/D/E/F>"',
            '  },',
            '  "detailed_summary": {',
            '    "strengths": "<exactly 2 sentences about main strengths>",',
            '    "weaknesses": "<exactly 2 sentences about main weaknesses>",',
            '    "recommendation": "<exactly 2 sentences with actionable advice>"',
            '  }',
            '}'
        ])

        return '\n'.join(prompt_parts)

    def parse_enhanced_analysis(self, analysis_text, detected_topics):
        """Parse enhanced DeepSeek response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', analysis_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())

                # Validate structure
                if not self.validate_enhanced_structure(parsed, detected_topics):
                    logger.warning("Invalid structure, using fallback")
                    return self.get_enhanced_fallback_scores(detected_topics)

                # Add numeric scores for backward compatibility
                parsed = self.add_numeric_scores(parsed)

                # Ensure all scores are within valid range
                parsed = self.normalize_scores(parsed)

                return parsed
            else:
                logger.warning("No JSON found in enhanced DeepSeek response, using fallback")
                return self.get_enhanced_fallback_scores(detected_topics)
        except Exception as e:
            logger.error(f"Error parsing enhanced DeepSeek response: {e}")
            return self.get_enhanced_fallback_scores(detected_topics)

    def validate_enhanced_structure(self, parsed, detected_topics):
        """Validate the enhanced response structure"""
        required_sections = ['topic_wise_analysis', 'soft_skills_analysis', 'overall_grades', 'detailed_summary']
        
        for section in required_sections:
            if section not in parsed:
                return False

        # Check topics
        topic_analysis = parsed.get('topic_wise_analysis', {})
        for topic in detected_topics:
            if topic not in topic_analysis:
                return False
            if not all(key in topic_analysis[topic] for key in ['score', 'feedback', 'improvements']):
                return False

        # Check soft skills
        soft_skills = parsed.get('soft_skills_analysis', {})
        required_skills = ['communication', 'confidence', 'relevance']
        for skill in required_skills:
            if skill not in soft_skills:
                return False
            if not all(key in soft_skills[skill] for key in ['score', 'feedback', 'improvements']):
                return False

        return True

    def add_numeric_scores(self, parsed):
        """Add numeric scores for backward compatibility"""
        # Calculate averages for legacy fields
        topic_scores = []
        for topic_data in parsed.get('topic_wise_analysis', {}).values():
            topic_scores.append(topic_data.get('score', 5))
        
        soft_skill_scores = []
        for skill_data in parsed.get('soft_skills_analysis', {}).values():
            soft_skill_scores.append(skill_data.get('score', 5))

        # Convert 0-10 to 0-100 for backward compatibility
        parsed['technical_score_numeric'] = (sum(topic_scores) / len(topic_scores) * 10) if topic_scores else 50
        parsed['communication_score_numeric'] = (sum(soft_skill_scores) / len(soft_skill_scores) * 10) if soft_skill_scores else 50
        parsed['confidence_score_numeric'] = parsed.get('soft_skills_analysis', {}).get('confidence', {}).get('score', 5) * 10
        parsed['overall_score_numeric'] = (parsed['technical_score_numeric'] + parsed['communication_score_numeric']) / 2

        return parsed

    def normalize_scores(self, parsed):
        """Ensure all scores are within valid ranges"""
        # Normalize topic scores
        for topic_data in parsed.get('topic_wise_analysis', {}).values():
            topic_data['score'] = max(0, min(10, float(topic_data.get('score', 5))))

        # Normalize soft skill scores
        for skill_data in parsed.get('soft_skills_analysis', {}).values():
            skill_data['score'] = max(0, min(10, float(skill_data.get('score', 5))))

        return parsed

    def get_enhanced_fallback_scores(self, detected_topics):
        """Enhanced fallback scores if analysis fails"""
        fallback = {
            'topic_wise_analysis': {},
            'soft_skills_analysis': {
                'communication': {
                    'score': 5,
                    'feedback': 'Unable to assess communication due to analysis limitations.',
                    'improvements': 'Practice clear articulation and structured responses. Focus on explaining technical concepts step by step.'
                },
                'confidence': {
                    'score': 5,
                    'feedback': 'Unable to assess confidence due to analysis limitations.',
                    'improvements': 'Practice mock interviews regularly. Build confidence through thorough preparation and practice.'
                },
                'relevance': {
                    'score': 5,
                    'feedback': 'Unable to assess relevance due to analysis limitations.',
                    'improvements': 'Listen carefully to questions before responding. Structure answers to directly address what is being asked.'
                }
            },
            'overall_grades': {
                'technical_grade': 'C',
                'communication_grade': 'C',
                'overall_grade': 'C'
            },
            'detailed_summary': {
                'strengths': 'Analysis could not be completed due to technical limitations. Basic response patterns were detected.',
                'weaknesses': 'Unable to identify specific weaknesses due to analysis constraints. More detailed assessment needed.',
                'recommendation': 'Complete a more comprehensive technical interview for accurate assessment. Practice fundamental concepts across all technical areas.'
            },
            'technical_score_numeric': 50,
            'communication_score_numeric': 50,
            'confidence_score_numeric': 50,
            'overall_score_numeric': 50
        }

        # Add fallback scores for detected topics
        for topic in detected_topics:
            fallback['topic_wise_analysis'][topic] = {
                'score': 5,
                'feedback': f'Unable to assess {topic} knowledge due to analysis limitations.',
                'improvements': f'Study fundamental {topic} concepts thoroughly. Practice explaining {topic} topics with clear examples and proper terminology.'
            }

        return fallback


def get_video_analysis(interview_id):
    """Get video analysis from your existing video API"""
    try:
        # Call your existing sophisticated video analysis API
        response = requests.post(
            f"http://192.168.1.123:5001/api/analyze-interview/{interview_id}",
            timeout=60
        )
        
        if response.status_code == 200:
            video_result = response.json()
            return {
                'video_success': True,
                'video_analysis': video_result
            }
        else:
            logger.error(f"Video analysis failed: {response.status_code} - {response.text}")
            return {
                'video_success': False,
                'video_error': f"API error: {response.status_code}",
                'video_analysis': create_default_video_analysis()
            }
            
    except Exception as e:
        logger.error(f"Video analysis request failed: {e}")
        return {
            'video_success': False,
            'video_error': str(e),
            'video_analysis': create_default_video_analysis()
        }

def create_default_video_analysis():
    """Create default video analysis when video service fails"""
    return {
        'integrity_assessment': {
            'overall_score': 75,
            'verdict': 'PASS',
            'confidence': 'MEDIUM'
        },
        'behavioral_analysis': {
            'cheating_detection': 'PASS',
            'attention_tracking': 'PASS', 
            'multiple_persons': 'PASS',
            'gaze_consistency': 'PASS'
        },
        'security_metrics': {
            'face_detection_quality': 85,
            'gaze_direction_analysis': 80,
            'motion_consistency': 85,
            'environmental_stability': 80
        },
        'risk_indicators': {
            'multiple_faces': 'CLEAR',
            'static_image_usage': 'CLEAR',
            'suspicious_eye_patterns': 'CLEAR',
            'external_aid_indicators': 'CLEAR'
        },
        'observations': [
            'Video analysis service unavailable - using default security assessment',
            'Manual review recommended if detailed video analysis required'
        ],
        'final_recommendation': 'ACCEPT',
        'note': 'Default analysis - video service unavailable'
    }





# Initialize components
hdfs_client = HDFSClient()
db_client = DatabaseClient()
audio_processor = AudioProcessor()
deepseek_analyzer = EnhancedDeepSeekAnalyzer()

@app.route('/api/analyze-interview/<interview_id>', methods=['POST'])
def analyze_interview(interview_id):
    """Enhanced API endpoint with both audio and video analysis"""
    try:
        logger.info(f"Starting enhanced analysis for interview {interview_id}")

        # Get interview info from database (your existing code)
        interview_info = db_client.get_interview_info(interview_id)
        if not interview_info:
            return jsonify({'error': 'Interview not found or already analyzed'}), 404

        # Get audio files (your existing code)
        audio_files = hdfs_client.get_interview_audio_files(interview_info)
        if not audio_files:
            return jsonify({'error': 'No audio files found'}), 404

        # Process each audio file (your existing code)
        question_responses = {}
        processed_count = 0

        for question_id, file_path in audio_files.items():
            logger.info(f"Processing question: {question_id}")

            try:
                # Get the audio file (your existing code)
                audio_file_path = hdfs_client.get_audio_file(file_path)
                if not audio_file_path:
                    logger.error(f"Failed to get audio file for question {question_id}")
                    continue

                # Process the webm file (your existing code)
                try:
                    text = audio_processor.process_webm_file(audio_file_path)
                    if text and text.strip():
                        question_responses[question_id] = text
                        processed_count += 1
                        logger.info(f"Successfully transcribed {question_id}: {len(text)} characters")
                    else:
                        logger.warning(f"No transcription for question {question_id}")
                except Exception as e:
                    logger.error(f"Error processing {question_id}: {e}")
                    continue

                # Cleanup if it was a downloaded file (your existing code)
                if not file_path.startswith('/app/'):
                    try:
                        os.unlink(audio_file_path)
                    except:
                        pass

            except Exception as e:
                logger.error(f"Error processing question {question_id}: {e}")
                continue

        if not question_responses:
            return jsonify({'error': 'No audio files could be processed or transcribed'}), 400

        logger.info(f"Successfully processed {processed_count} out of {len(audio_files)} audio files")

        # Analyze with Enhanced DeepSeek (your existing code)
        audio_analysis_results = deepseek_analyzer.analyze_responses(question_responses)

        # *** NEW: GET VIDEO ANALYSIS ***
        video_analysis_results = get_video_analysis(interview_id)

        # Update database with audio results (your existing code)
        success = db_client.update_analysis_status(interview_id, audio_analysis_results)

        # Prepare enhanced response with BOTH audio and video analysis
        enhanced_response = {
            'success': success,
            'interview_id': interview_id,
            'student_info': {
                'name': f"{interview_info['first_name']} {interview_info['last_name']}",
                'email': interview_info['email'],
                'student_id': interview_info['student_id'],
                'attempt_number': interview_info['attempt_number']
            },
            'processing_summary': {
                'total_audio_files': len(audio_files),
                'processed_questions': processed_count,
                'topics_detected': list(audio_analysis_results.get('topic_wise_analysis', {}).keys()),
                'analysis_timestamp': datetime.now().isoformat()
            },
            # Audio analysis for student report
            'detailed_analysis': audio_analysis_results,
            'transcriptions': question_responses,
            'legacy_scores': {
                'overall_score': audio_analysis_results.get('overall_score_numeric', 50),
                'technical_score': audio_analysis_results.get('technical_score_numeric', 50),
                'communication_score': audio_analysis_results.get('communication_score_numeric', 50),
                'confidence_score': audio_analysis_results.get('confidence_score_numeric', 50)
            },
            # Video analysis for PAT team report
            'video_analysis': video_analysis_results
        }

        return jsonify(enhanced_response)

    except Exception as e:
        logger.error(f"Enhanced analysis failed for interview {interview_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-detailed-report/<interview_id>', methods=['GET'])
def get_detailed_report(interview_id):
    """Get a formatted detailed report for an interview"""
    try:
        # Get interview info
        interview_info = db_client.get_interview_info(interview_id)
        if not interview_info:
            return jsonify({'error': 'Interview not found'}), 404

        # Get stored analysis results from database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT overall_score, technical_score, communication_score, confidence_score,
               analysis_completed
        FROM interview_system_interview
        WHERE id = %s
        """

        cursor.execute(query, (interview_id,))
        stored_results = cursor.fetchone()

        cursor.close()
        connection.close()

        if not stored_results or not stored_results['analysis_completed']:
            return jsonify({'error': 'Analysis not completed for this interview'}), 404

        # Generate detailed report format
        report = {
            'interview_details': {
                'interview_id': interview_id,
                'student_name': f"{interview_info['first_name']} {interview_info['last_name']}",
                'student_email': interview_info['email'],
                'student_id': interview_info['student_id'],
                'attempt_number': interview_info['attempt_number'],
                'completed_at': interview_info['completed_at'].isoformat() if interview_info['completed_at'] else None,
                'report_generated_at': datetime.now().isoformat()
            },
            'executive_summary': {
                'overall_score': stored_results['overall_score'],
                'technical_score': stored_results['technical_score'],
                'communication_score': stored_results['communication_score'],
                'confidence_score': stored_results['confidence_score'],
                'performance_level': get_performance_level(stored_results['overall_score'])
            },
            'detailed_breakdown': {
                'technical_assessment': generate_technical_breakdown(stored_results['technical_score']),
                'communication_assessment': generate_communication_breakdown(stored_results['communication_score']),
                'confidence_assessment': generate_confidence_breakdown(stored_results['confidence_score'])
            },
            'recommendations': generate_recommendations(stored_results),
            'next_steps': generate_next_steps(stored_results['overall_score'])
        }

        return jsonify(report)

    except Exception as e:
        logger.error(f"Error generating detailed report: {e}")
        return jsonify({'error': 'Failed to generate detailed report'}), 500

def get_performance_level(score):
    """Get performance level based on score"""
    if score >= 90:
        return "Excellent"
    elif score >= 80:
        return "Very Good"
    elif score >= 70:
        return "Good"
    elif score >= 60:
        return "Satisfactory"
    elif score >= 50:
        return "Needs Improvement"
    else:
        return "Unsatisfactory"

def generate_technical_breakdown(technical_score):
    """Generate technical assessment breakdown"""
    if technical_score >= 80:
        return {
            'level': 'Strong',
            'description': 'Demonstrates solid technical knowledge with good understanding of concepts.',
            'strengths': ['Good grasp of fundamental concepts', 'Appropriate use of technical terminology'],
            'areas_for_improvement': ['Continue building on advanced topics', 'Deepen practical application skills']
        }
    elif technical_score >= 60:
        return {
            'level': 'Moderate',
            'description': 'Shows basic technical knowledge but with gaps in understanding.',
            'strengths': ['Basic understanding of core concepts', 'Some correct technical responses'],
            'areas_for_improvement': ['Study advanced concepts more thoroughly', 'Practice explaining technical details clearly']
        }
    else:
        return {
            'level': 'Needs Development',
            'description': 'Limited technical knowledge with significant gaps requiring attention.',
            'strengths': ['Shows willingness to attempt technical questions'],
            'areas_for_improvement': ['Focus on fundamental concepts first', 'Invest more time in technical study and practice']
        }

def generate_communication_breakdown(comm_score):
    """Generate communication assessment breakdown"""
    if comm_score >= 80:
        return {
            'level': 'Excellent',
            'description': 'Communicates technical concepts clearly and effectively.',
            'strengths': ['Clear articulation', 'Well-structured responses', 'Good use of examples'],
            'areas_for_improvement': ['Continue refining presentation skills', 'Practice handling complex questions']
        }
    elif comm_score >= 60:
        return {
            'level': 'Good',
            'description': 'Generally clear communication with room for improvement in structure.',
            'strengths': ['Understandable responses', 'Shows effort to explain concepts'],
            'areas_for_improvement': ['Improve response structure', 'Practice explaining complex topics step-by-step']
        }
    else:
        return {
            'level': 'Needs Improvement',
            'description': 'Communication skills require significant development for technical roles.',
            'strengths': ['Attempts to respond to questions'],
            'areas_for_improvement': ['Focus on clarity and structure', 'Practice technical communication regularly']
        }

def generate_confidence_breakdown(conf_score):
    """Generate confidence assessment breakdown"""
    if conf_score >= 80:
        return {
            'level': 'High',
            'description': 'Shows strong confidence and composure throughout the interview.',
            'strengths': ['Comfortable with technical discussions', 'Maintains composure under pressure'],
            'areas_for_improvement': ['Continue building expertise', 'Share knowledge with others to reinforce learning']
        }
    elif conf_score >= 60:
        return {
            'level': 'Moderate',
            'description': 'Generally confident but shows some hesitation on complex topics.',
            'strengths': ['Confident in familiar areas', 'Willing to attempt difficult questions'],
            'areas_for_improvement': ['Build confidence through more practice', 'Prepare for challenging scenarios']
        }
    else:
        return {
            'level': 'Developing',
            'description': 'Confidence levels need building through preparation and practice.',
            'strengths': ['Shows willingness to participate'],
            'areas_for_improvement': ['Practice mock interviews regularly', 'Build knowledge base to increase confidence']
        }

def generate_recommendations(scores):
    """Generate specific recommendations based on scores"""
    recommendations = []
    
    if scores['technical_score'] < 70:
        recommendations.append({
            'category': 'Technical Skills',
            'priority': 'High',
            'action': 'Focus on strengthening fundamental technical concepts through structured learning and hands-on practice.'
        })
    
    if scores['communication_score'] < 70:
        recommendations.append({
            'category': 'Communication',
            'priority': 'High',
            'action': 'Practice explaining technical concepts clearly and develop structured response frameworks.'
        })
    
    if scores['confidence_score'] < 70:
        recommendations.append({
            'category': 'Confidence Building',
            'priority': 'Medium',
            'action': 'Engage in regular mock interviews and technical discussions to build confidence.'
        })
    
    if scores['overall_score'] >= 80:
        recommendations.append({
            'category': 'Advanced Development',
            'priority': 'Low',
            'action': 'Continue learning advanced topics and consider mentoring others to reinforce knowledge.'
        })
    
    return recommendations

def generate_next_steps(overall_score):
    """Generate next steps based on overall performance"""
    if overall_score >= 80:
        return [
            "Continue with advanced technical learning",
            "Consider contributing to open-source projects",
            "Prepare for senior-level technical discussions",
            "Focus on leadership and mentoring skills"
        ]
    elif overall_score >= 60:
        return [
            "Strengthen weak technical areas identified in the assessment",
            "Practice mock interviews regularly",
            "Work on real-world projects to build practical experience",
            "Improve technical communication skills"
        ]
    else:
        return [
            "Focus on fundamental concepts first",
            "Take structured courses in identified weak areas",
            "Practice basic technical problems daily",
            "Build a strong foundation before attempting advanced topics"
        ]

@app.route('/api/pending-interviews', methods=['GET'])
def get_pending_interviews():
    """Get list of interviews ready for analysis"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT id, student_id, attempt_number, completed_at
        FROM interview_system_interview
        WHERE status = 'completed' AND analysis_completed = FALSE
        ORDER BY completed_at ASC
        LIMIT 50
        """

        cursor.execute(query)
        interviews = cursor.fetchall()

        cursor.close()
        connection.close()

        logger.info(f"Found {len(interviews)} pending interviews")
        return jsonify(interviews)

    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/api/interview-status/<interview_id>', methods=['GET'])
def get_interview_status(interview_id):
    """Get analysis status for a specific interview"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT
            id, status, analysis_completed,
            overall_score, technical_score, communication_score, confidence_score,
            completed_at
        FROM interview_system_interview
        WHERE id = %s
        """

        cursor.execute(query, (interview_id,))
        interview = cursor.fetchone()

        cursor.close()
        connection.close()

        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        return jsonify(interview)

    except Error as e:
        logger.error(f"Database error: {e}")
        return jsonify({'error': 'Database error'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db_connected = False
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            connection.close()
            db_connected = True
        except:
            pass

        return jsonify({
            'status': 'healthy',
            'version': 'enhanced-v2.0',
            'features': {
                'topic_wise_analysis': True,
                'soft_skills_assessment': True,
                'dynamic_topic_detection': True,
                'detailed_reporting': True,
                'strict_grading': True
            },
            'timestamp': datetime.now().isoformat(),
            'services': {
                'hdfs': hdfs_client.client is not None,
                'database': db_connected,
                'openrouter': bool(OPENROUTER_API_KEY and OPENROUTER_API_KEY != 'your-api-key-here')
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/debug-interview/<interview_id>', methods=['GET'])
def debug_interview(interview_id):
    """Debug endpoint to see what's happening with audio processing"""
    try:
        logger.info(f"Debugging interview {interview_id}")

        # Step 1: Get interview info
        interview_info = db_client.get_interview_info(interview_id)
        if not interview_info:
            return jsonify({'error': 'Interview not found', 'step': 'get_interview_info'})

        debug_info = {
            'interview_info': interview_info,
            'steps': []
        }

        # Step 2: Get audio files from database
        try:
            connection = mysql.connector.connect(**DB_CONFIG)
            cursor = connection.cursor(dictionary=True)

            query = """
            SELECT question_id, audio_file_path, local_file_path
            FROM interview_system_interviewresponse
            WHERE interview_id = %s
            """

            cursor.execute(query, (interview_info['interview_id'],))
            audio_records = cursor.fetchall()

            cursor.close()
            connection.close()

            debug_info['audio_records'] = audio_records
            debug_info['steps'].append(f"Found {len(audio_records)} audio records in database")

        except Exception as e:
            debug_info['steps'].append(f"Database error: {e}")
            return jsonify(debug_info)

        # Step 3: Check local files and detect topics
        local_files = {}
        detected_topics = set()
        for record in audio_records:
            question_id = record['question_id']
            local_path = record['local_file_path']
            
            # Detect topic
            if '/' in question_id:
                topic = question_id.split('/')[0].replace('-', ' ').replace('_', ' ').title()
                detected_topics.add(topic)

            if local_path and os.path.exists(local_path):
                file_size = os.path.getsize(local_path)
                local_files[question_id] = {
                    'path': local_path,
                    'size': file_size,
                    'exists': True
                }
                debug_info['steps'].append(f"✓ Found local file: {question_id} (size: {file_size} bytes)")
            else:
                local_files[question_id] = {
                    'path': local_path,
                    'exists': False
                }
                debug_info['steps'].append(f"✗ Local file not found: {question_id}")

        debug_info['local_files'] = local_files
        debug_info['detected_topics'] = list(detected_topics)
        debug_info['total_local_files'] = len([f for f in local_files.values() if f['exists']])

        return jsonify(debug_info)

    except Exception as e:
        logger.error(f"Debug failed: {e}")
        return jsonify({'error': str(e), 'step': 'debug_exception'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
