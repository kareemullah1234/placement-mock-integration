import json
import os
from datetime import datetime
from django.conf import settings
from utils.hdfs_client import HDFSClient
from .models import Interview, VoiceInterviewSession
import logging

logger = logging.getLogger(__name__)

class InterviewSessionManager:
    """Manages complete interview session storage in JSON format"""

    def __init__(self):
        self.hdfs_client = HDFSClient()

    def create_session_json(self, interview_id):
        """Create complete interview session JSON"""
        try:
            interview = Interview.objects.get(id=interview_id)
            voice_session = VoiceInterviewSession.objects.filter(interview=interview).first()

            # Get student info
            student = interview.student
            student_profile = getattr(student, 'student_profile', None)
            student_id = student_profile.student_id if student_profile else 'UNKNOWN'
            student_name = f"{student.first_name}_{student.last_name}".replace(' ', '_')

            # Create session structure
            session_data = {
                "interview_metadata": {
                    "interview_id": interview.id,
                    "student_name": student.get_full_name(),
                    "student_id": student_id,
                    "student_username": student.username,
                    "attempt_number": interview.attempt_number,
                    "created_at": interview.created_at.isoformat(),
                    "started_at": interview.started_at.isoformat() if interview.started_at else None,
                    "completed_at": interview.completed_at.isoformat() if interview.completed_at else None,
                    "status": interview.status,
                    "overall_score": interview.overall_score,
                    "technical_score": interview.technical_score,
                    "communication_score": interview.communication_score,
                    "confidence_score": interview.confidence_score,
                    "cheating_detected": interview.cheating_detected,
                    "analysis_completed": interview.analysis_completed
                },
                "interview_questions": {},
                "video_recording": {
                    "video_file_path": None,
                    "local_video_file_path": None,
                    "video_saved_to_hdfs": False,
                    "total_video_chunks": 0,
                },
                "session_summary": {
                    "total_questions": 0,
                    "questions_answered": 0,
                    "total_duration_minutes": 0,
                    "audio_responses_stored": 0,
                    "video_recording_stored": False,
                }
            }

            # Process voice session if exists
            if voice_session and voice_session.interview_context:
                self._process_voice_session(session_data, voice_session)

            # Calculate summary
            self._calculate_session_summary(session_data, interview)

            # Store in HDFS
            filename = f"{student_name}_{student_id}_attempt_{interview.attempt_number}_interview_{interview.id}.json"
            hdfs_path = self._store_session_json(session_data, filename)

            # Store audio responses separately
            audio_storage_path = self._store_audio_responses(interview, student_name, student_id)
            local_video_path = self._get_local_video_path(interview)
            video_storage_path = self._store_video_recording(interview, local_video_path, student_name, student_id)

            frames = getattr(interview, 'frames', None)
            session_data["video_recording"] = {
                "video_file_path": video_storage_path or local_video_path,
                "local_video_file_path": local_video_path,
                "video_saved_to_hdfs": bool(video_storage_path and video_storage_path.startswith('/student_video_recordings/')),
                "total_video_chunks": frames.total_video_chunks if frames else 0,
            }

            session_data["storage_info"] = {
                "json_hdfs_path": hdfs_path,
                "audio_storage_path": audio_storage_path,
                "video_storage_path": video_storage_path,
                "local_video_path": local_video_path,
                "stored_at": datetime.now().isoformat()
            }

            return session_data

        except Exception as e:
            logger.error(f"Error creating session JSON for interview {interview_id}: {e}")
            return None

    def _process_voice_session(self, session_data, voice_session):
        """Process voice interview session data"""
        try:
            from .models import InterviewResponse

            # Get all interview context entries
            if isinstance(voice_session.interview_context, list):
                contexts = voice_session.interview_context
            else:
                contexts = voice_session.interview_context.get('questions', []) if voice_session.interview_context else []
            
            interview = voice_session.interview
            responses_by_question = {
                response.question_id: response
                for response in InterviewResponse.objects.filter(interview=interview).select_related('question')
            }
            
            for context in contexts:
                question_num = context.get('question_number', 0)
                question_id = context.get('question_id')
                response = responses_by_question.get(question_id)
                
                session_data["interview_questions"][f"question_{question_num}"] = {
                    "question_number": question_num,
                    "stage": self._determine_stage(question_num),
                    "ai_question": context.get('ai_question', ''),
                    "human_response": context.get('response', ''),
                    "timestamp": context.get('timestamp', ''),
                    "audio_file_path": response.audio_file_path if response else None,
                    "local_audio_file_path": response.local_file_path if response else None,
                    "audio_saved_to_hdfs": bool(response and response.audio_file_path and response.audio_file_path.startswith('/student_audio_responses/'))
                }
                    
        except Exception as e:
            logger.error(f"Error processing voice session: {e}")

    def _determine_stage(self, question_number):
        """Determine interview stage based on question number"""
        if 1 <= question_number <= 3:
            return "intro"
        elif 4 <= question_number <= 6:
            return "projects"
        elif 7 <= question_number <= 9:
            return "python"
        elif 10 <= question_number <= 12:
            return "statistics"
        elif 13 <= question_number <= 14:
            return "ml"
        elif question_number == 15:
            return "closing"
        else:
            return "unknown"

    def _calculate_session_summary(self, session_data, interview):
        """Calculate session summary statistics"""
        questions = session_data["interview_questions"]

        session_data["session_summary"] = {
            "total_questions": len(questions),
            "questions_answered": len([q for q in questions.values() if q.get('human_response')]),
            "total_duration_minutes": self._calculate_duration(interview),
            "audio_responses_stored": len([q for q in questions.values() if q.get('human_response')]),
            "video_recording_stored": bool(session_data.get("video_recording", {}).get("video_file_path")),
        }

    def _calculate_duration(self, interview):
        """Calculate interview duration in minutes"""
        if interview.started_at and interview.completed_at:
            duration = interview.completed_at - interview.started_at
            return round(duration.total_seconds() / 60, 2)
        return 0

    def _store_session_json(self, session_data, filename):
        """Store session JSON in HDFS"""
        try:
            if self.hdfs_client.is_connected():
                # Create JSON string
                json_content = json.dumps(session_data, indent=2, ensure_ascii=False)

                # Store in HDFS under /interview_sessions/
                hdfs_path = f"/interview_sessions/{filename}"

                logger.info(f"Attempting to store session JSON at: {hdfs_path}")
                logger.info(f"JSON content size: {len(json_content)} characters")

                # Write to HDFS
                success = self.hdfs_client.write_file(hdfs_path, json_content.encode('utf-8'))

                if success:
                    logger.info(f"Session JSON stored successfully at: {hdfs_path}")
                    return hdfs_path
                else:
                    logger.error("Failed to store session JSON in HDFS - write_file returned False")
                    return self._store_session_locally(session_data, filename)
            else:
                logger.warning("HDFS not connected, storing locally")
                return self._store_session_locally(session_data, filename)

        except Exception as e:
            logger.error(f"Error storing session JSON: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return self._store_session_locally(session_data, filename)

    def _store_session_locally(self, session_data, filename):
        """Fallback: store session JSON locally"""
        try:
            local_dir = os.path.join(settings.BASE_DIR, 'interview_sessions')
            os.makedirs(local_dir, exist_ok=True)

            local_path = os.path.join(local_dir, filename)

            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            logger.info(f"Session JSON stored locally at: {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"Error storing session locally: {e}")
            return None

    def _store_audio_responses(self, interview, student_name, student_id):
        """Store audio responses in organized HDFS structure - HDFS only"""
        try:
            from .models import InterviewResponse
            
            # Create HDFS directory structure
            audio_dir = f"/student_audio_responses/{student_name}_{student_id}_attempt_{interview.attempt_number}"
            
            # Get all audio responses for this interview
            responses = InterviewResponse.objects.filter(interview=interview)
            
            stored_count = 0
            for response in responses:
                # Check if audio is already stored in HDFS
                if response.audio_file_path and response.audio_file_path.startswith('/student_audio_responses/'):
                    # Verify the file actually exists in HDFS
                    try:
                        if self.hdfs_client.is_connected():
                            # Check if file exists
                            self.hdfs_client.client.status(response.audio_file_path)
                            stored_count += 1
                            logger.info(f"Verified audio in HDFS: {response.audio_file_path}")
                        else:
                            logger.warning(f"HDFS not connected - cannot verify: {response.audio_file_path}")
                    except Exception as verify_error:
                        logger.warning(f"Audio file not found in HDFS: {response.audio_file_path} - {verify_error}")
                else:
                    logger.warning(f"Audio response has no HDFS path: {response.question_id}")
            
            logger.info(f"Verified {stored_count} audio responses in HDFS: {audio_dir}")
            return audio_dir if stored_count > 0 else None
            
        except Exception as e:
            logger.error(f"Error processing audio responses: {e}")
            return None

    def _get_local_video_path(self, interview):
        """Return local fallback video path if it exists."""
        local_path = os.path.join(settings.MEDIA_ROOT, 'video_recordings', f'interview_{interview.id}.webm')
        return local_path if os.path.exists(local_path) else None

    def _store_video_recording(self, interview, local_video_path, student_name, student_id):
        """Store final interview video in HDFS when a local recording exists."""
        if not local_video_path or not os.path.exists(local_video_path):
            return None

        try:
            if not self.hdfs_client.is_connected():
                logger.warning("HDFS not connected, skipping video upload")
                return None

            folder_name = f"{student_name}_{student_id}_attempt_{interview.attempt_number}"
            hdfs_path = f"/student_video_recordings/{folder_name}/interview_{interview.id}.webm"

            with open(local_video_path, 'rb') as video_file:
                video_bytes = video_file.read()

            if self.hdfs_client.write_file(hdfs_path, video_bytes):
                logger.info(f"Stored interview video in HDFS: {hdfs_path}")
                return hdfs_path
        except Exception as e:
            logger.error(f"Error storing video recording for interview {interview.id}: {e}")

        return None
