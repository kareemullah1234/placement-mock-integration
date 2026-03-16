from django.db import models
from interview_system.models import Interview
import uuid

class AnalysisResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='analysis_result')
    
    # Computer Vision Results
    cv_score = models.FloatField(default=0)
    face_detection_score = models.FloatField(default=0)
    eye_movement_score = models.FloatField(default=0)
    head_movement_score = models.FloatField(default=0)
    
    # Transcript Analysis Results
    transcript_score = models.FloatField(default=0)
    content_quality_score = models.FloatField(default=0)
    fluency_score = models.FloatField(default=0)
    
    # Overall Assessment
    final_score = models.FloatField(default=0)
    grade = models.CharField(max_length=2, blank=True)
    
    # Analysis Details
    analysis_details = models.JSONField(default=dict)
    processed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Analysis for {self.interview}"
