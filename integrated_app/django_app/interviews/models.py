from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()

class Interview(models.Model):
    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('incomplete', 'Incomplete'),  # Student ended early or abandoned
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    COMPLETION_REASON_CHOICES = [
        ('all_questions_answered', 'All Questions Answered'),
        ('user_ended_early', 'User Ended Early'),
        ('timeout', 'Session Timeout'),
        ('error', 'Technical Error'),
        ('admin_cancelled', 'Admin Cancelled'),
        ('expired', 'Interview Expired'),
        ('not_started', 'Never Started'),
    ]
    
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending Processing'),
        ('processing', 'Processing'),
        ('analysis_complete', 'Analysis Complete'),
        ('report_generated', 'Report Generated'),
        ('report_sent', 'Report Sent'),
        ('failed', 'Processing Failed'),
    ]

    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviews')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    attempt_number = models.IntegerField(default=1)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Admin fields
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_interviews')
    admin_notes = models.TextField(blank=True)

    # ========== NEW: Interview Completion Tracking ==========
    # Question/Response tracking
    total_questions = models.IntegerField(default=15, help_text="Total questions in the interview")
    questions_answered = models.IntegerField(default=0, help_text="Number of questions answered by student")
    voice_interview_started = models.BooleanField(default=False, help_text="Did student start voice interview?")
    voice_interview_completed = models.BooleanField(default=False, help_text="Did student complete all questions?")
    
    # Completion details
    completion_reason = models.CharField(
        max_length=30, 
        choices=COMPLETION_REASON_CHOICES, 
        null=True, 
        blank=True,
        help_text="Why the interview ended"
    )
    completion_percentage = models.FloatField(default=0.0, help_text="Percentage of interview completed (0-100)")
    
    # Duration tracking
    interview_duration_seconds = models.IntegerField(null=True, blank=True, help_text="Total interview duration in seconds")
    
    # Data availability flags (for DAG processing)
    has_audio_responses = models.BooleanField(default=False, help_text="Are audio responses saved in HDFS?")
    has_video_recording = models.BooleanField(default=False, help_text="Is video recording available in Kafka?")
    has_frame_data = models.BooleanField(default=False, help_text="Are frames available for analysis?")
    audio_responses_count = models.IntegerField(default=0, help_text="Number of audio files saved")
    
    # Processing status (for DAG tracking)
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending',
        help_text="Current processing status in pipeline"
    )
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    processing_error = models.TextField(blank=True, null=True, help_text="Error message if processing failed")
    
    # Report tracking
    report_generated_at = models.DateTimeField(null=True, blank=True)
    report_file_path = models.TextField(blank=True, null=True, help_text="Path to generated PDF report")
    report_sent_at = models.DateTimeField(null=True, blank=True)
    report_sent_to = models.EmailField(blank=True, null=True, help_text="Email address report was sent to")
    
    # Email tracking (for optimized email DAG)
    approval_email_sent = models.BooleanField(default=False, help_text="Has approval email been sent?")
    approval_email_sent_at = models.DateTimeField(null=True, blank=True)
    rejection_email_sent = models.BooleanField(default=False, help_text="Has rejection email been sent?")
    rejection_email_sent_at = models.DateTimeField(null=True, blank=True)
    status_updated_at = models.DateTimeField(auto_now=True, help_text="Last status change timestamp")
    
    # ========== END: New Fields ==========

    # Analysis results
    overall_score = models.FloatField(null=True, blank=True)
    technical_score = models.FloatField(null=True, blank=True)
    communication_score = models.FloatField(null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)
    cheating_detected = models.BooleanField(default=False)
    analysis_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'interview_system_interview'
        ordering = ['-created_at']

    def __str__(self):
        return f"Interview {self.id} - {self.student.get_full_name()} (Attempt {self.attempt_number})"

    def is_expired(self):
        """Check if interview has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def time_remaining(self):
        """Get time remaining in minutes"""
        if self.expires_at and self.status == 'approved':
            remaining = (self.expires_at - timezone.now()).total_seconds()
            return max(0, int(remaining / 60))
        return 0
    
    def update_completion_stats(self):
        """Update completion statistics based on current state"""
        # Calculate completion percentage
        if self.total_questions > 0:
            self.completion_percentage = (self.questions_answered / self.total_questions) * 100
        
        # Check if voice interview is completed
        self.voice_interview_completed = self.questions_answered >= self.total_questions
        
        # Calculate duration if started and completed
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
            self.interview_duration_seconds = int(duration)
        
        # Update audio response count from related responses
        self.audio_responses_count = self.responses.count()
        self.has_audio_responses = self.audio_responses_count > 0
        
        # Check video/frame data from related frames record
        if hasattr(self, 'frames') and self.frames:
            self.has_video_recording = self.frames.total_video_chunks > 0
            self.has_frame_data = self.frames.total_frames > 0
    
    def is_ready_for_processing(self):
        """Check if interview has enough data for DAG processing"""
        return (
            self.status in ['completed', 'incomplete'] and
            self.processing_status == 'pending' and
            (self.has_audio_responses or self.has_video_recording or self.has_frame_data) and
            self.questions_answered > 0
        )
    
    def get_completion_summary(self):
        """Get a summary of interview completion status"""
        return {
            'interview_id': self.id,
            'status': self.status,
            'questions_answered': self.questions_answered,
            'total_questions': self.total_questions,
            'completion_percentage': self.completion_percentage,
            'voice_interview_completed': self.voice_interview_completed,
            'completion_reason': self.completion_reason,
            'has_audio': self.has_audio_responses,
            'has_video': self.has_video_recording,
            'has_frames': self.has_frame_data,
            'processing_status': self.processing_status,
            'is_ready_for_processing': self.is_ready_for_processing(),
        }

class InterviewResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.ForeignKey(
        Interview,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        related_name='responses'
    )
    audio_file_path = models.TextField()
    local_file_path = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'interview_system_interviewresponse'

    def __str__(self):
        return f"Response {self.id} - {self.question.question_text[:30]}"

class InterviewFrames(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='frames')
    frames_file_path = models.TextField(blank=True, null=True)  # HDFS path (now optional)
    total_frames = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    # Kafka session IDs - UPDATED FIELDS
    kafka_session_id = models.CharField(max_length=255, blank=True, null=True, help_text="Session ID for frame streaming")
    video_session_id = models.CharField(max_length=255, blank=True, null=True, help_text="Session ID for video chunk streaming")
    
    # Storage method and additional metadata
    storage_method = models.CharField(
        max_length=20,
        choices=[('hdfs', 'HDFS'), ('kafka', 'Kafka'), ('both', 'Both')],
        default='hdfs'
    )
    
    # Video-specific fields
    total_video_chunks = models.IntegerField(default=0, help_text="Number of video chunks recorded")
    video_recording_started_at = models.DateTimeField(null=True, blank=True)
    video_recording_ended_at = models.DateTimeField(null=True, blank=True)
    estimated_video_duration_seconds = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'interview_system_interviewframes'

    def __str__(self):
        return f"Frames {self.id} - {self.total_frames} frames, {self.total_video_chunks} chunks ({self.storage_method})"

# (Keep all your existing models, just add these at the bottom)

class VoiceInterviewSession(models.Model):
    """Voice interview session tracking"""
    
    STAGE_CHOICES = [
        ('intro', 'Introduction'),
        ('projects', 'Projects'),
        ('python', 'Python Skills'),
        ('statistics', 'Statistics'),
        ('ml', 'Machine Learning'),
        ('closing', 'Closing'),
    ]
    
    SESSION_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('error', 'Error'),
    ]
    
    interview = models.OneToOneField(
        'Interview', 
        on_delete=models.CASCADE, 
        related_name='voice_session'
    )
    current_question_number = models.IntegerField(default=0)
    current_stage = models.CharField(
        max_length=20, 
        choices=STAGE_CHOICES,
        default='intro'
    )
    interview_context = models.JSONField(default=list)
    session_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # ========== NEW: Enhanced Session Tracking ==========
    session_status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS_CHOICES,
        default='not_started',
        help_text="Current status of voice interview session"
    )
    
    # Question tracking
    total_questions_in_session = models.IntegerField(default=15)
    questions_with_audio_saved = models.IntegerField(default=0, help_text="Questions with audio successfully saved to HDFS")
    last_question_answered_at = models.DateTimeField(null=True, blank=True)
    
    # Session timing
    voice_session_started_at = models.DateTimeField(null=True, blank=True)
    voice_session_ended_at = models.DateTimeField(null=True, blank=True)
    
    # End reason
    end_reason = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Why the session ended: 'completed', 'user_ended', 'timeout', 'error'"
    )
    
    # Error tracking
    last_error = models.TextField(blank=True, null=True)
    error_count = models.IntegerField(default=0)
    # ========== END: New Fields ==========
    
    class Meta:
        db_table = 'voice_interview_sessions'
    
    def __str__(self):
        return f"Voice Session for Interview {self.interview.id} - Q{self.current_question_number} ({self.current_stage}) [{self.session_status}]"
    
    def get_progress_percentage(self):
        if self.total_questions_in_session > 0:
            return int((self.current_question_number / self.total_questions_in_session) * 100)
        return 0
    
    def is_completed(self):
        return self.current_question_number >= self.total_questions_in_session
    
    def start_session(self):
        """Mark session as started"""
        self.session_status = 'in_progress'
        self.voice_session_started_at = timezone.now()
        self.save()
        
        # Also update parent Interview
        self.interview.voice_interview_started = True
        self.interview.save(update_fields=['voice_interview_started'])
    
    def complete_session(self, reason='completed'):
        """Mark session as completed"""
        self.session_status = 'completed' if self.is_completed() else 'abandoned'
        self.voice_session_ended_at = timezone.now()
        self.end_reason = reason
        self.save()
        
        # Update parent Interview with completion stats
        self.sync_to_interview()
    
    def sync_to_interview(self):
        """Sync session data to parent Interview model"""
        interview = self.interview
        
        # Update question counts
        interview.questions_answered = self.current_question_number
        interview.voice_interview_completed = self.is_completed()
        
        # Set completion reason based on session
        if self.is_completed():
            interview.completion_reason = 'all_questions_answered'
        elif self.end_reason == 'user_ended':
            interview.completion_reason = 'user_ended_early'
        elif self.end_reason == 'timeout':
            interview.completion_reason = 'timeout'
        elif self.end_reason == 'error':
            interview.completion_reason = 'error'
        
        # Update audio count
        interview.audio_responses_count = self.questions_with_audio_saved
        interview.has_audio_responses = self.questions_with_audio_saved > 0
        
        # Calculate completion percentage
        interview.update_completion_stats()
        
        interview.save()
    
    def record_question_answered(self, audio_saved=False):
        """Record that a question was answered"""
        self.last_question_answered_at = timezone.now()
        if audio_saved:
            self.questions_with_audio_saved += 1
        self.save()
    
    def get_session_summary(self):
        """Get summary of session for reporting"""
        duration = None
        if self.voice_session_started_at and self.voice_session_ended_at:
            duration = (self.voice_session_ended_at - self.voice_session_started_at).total_seconds()
        
        return {
            'session_status': self.session_status,
            'current_question': self.current_question_number,
            'total_questions': self.total_questions_in_session,
            'progress_percentage': self.get_progress_percentage(),
            'is_completed': self.is_completed(),
            'questions_with_audio': self.questions_with_audio_saved,
            'session_duration_seconds': duration,
            'end_reason': self.end_reason,
            'current_stage': self.current_stage,
            'error_count': self.error_count,
        }
class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question_text = models.TextField()
    category = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=50)

    class Meta:
        db_table = 'interview_system_question'

    def __str__(self):
        return self.question_text[:60]
