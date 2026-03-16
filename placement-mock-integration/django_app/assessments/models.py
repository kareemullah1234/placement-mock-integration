from django.db import models
from companies.models import JobPost
from applications.models import Application

class AptitudeTest(models.Model):
    job = models.OneToOneField(JobPost, on_delete=models.CASCADE)
    total_questions = models.IntegerField()
    total_marks = models.IntegerField()
    passing_marks = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

class CandidateTestAttempt(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE)
    score = models.IntegerField()
    passed = models.BooleanField()
    attempted_at = models.DateTimeField(auto_now_add=True)