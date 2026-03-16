from django.db import models
from candidates.models import CandidateProfile
from companies.models import JobPost

class Application(models.Model):
    STATUS_CHOICES = [
        ('applied', 'Applied'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('aptitude_passed', 'Aptitude Passed'),
        ('aptitude_failed', 'Aptitude Failed'),
        ('mock_passed', 'Mock Passed'),
        ('mock_failed', 'Mock Failed'),
        ('final_selected', 'Final Selected'),
    ]

    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE)
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    test_scheduled_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)