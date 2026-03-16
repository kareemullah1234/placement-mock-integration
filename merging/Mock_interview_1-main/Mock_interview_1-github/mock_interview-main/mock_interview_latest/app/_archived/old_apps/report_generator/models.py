from django.db import models
from django.contrib.auth import get_user_model
from interview_system.models import Interview
import uuid

User = get_user_model()

class InterviewReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='report')
    
    # Overall Assessment
    final_grade = models.CharField(max_length=2, blank=True)  # A+, A, B, C, D, F
    overall_feedback = models.TextField(blank=True)
    
    # Detailed Scores
    technical_score = models.FloatField(default=0)
    communication_score = models.FloatField(default=0)
    behavioral_score = models.FloatField(default=0)
    
    # Cheating Analysis
    integrity_score = models.FloatField(default=100)  # 100 = no cheating detected
    suspicious_activities = models.JSONField(default=list)
    
    # Recommendations
    strengths = models.JSONField(default=list)
    areas_for_improvement = models.JSONField(default=list)
    recommended_resources = models.JSONField(default=list)
    
    # Report Generation
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"Report for {self.interview}"

class SystemAnalytics(models.Model):
    date = models.DateField(unique=True)
    total_interviews = models.IntegerField(default=0)
    completed_interviews = models.IntegerField(default=0)
    average_score = models.FloatField(default=0)
    cheating_incidents = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for {self.date}"
