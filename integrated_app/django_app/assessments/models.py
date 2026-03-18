from django.db import models
from companies.models import JobPost
from applications.models import Application

class AptitudeTest(models.Model):
    job = models.OneToOneField(JobPost, on_delete=models.CASCADE)
    total_questions = models.IntegerField()
    total_marks = models.IntegerField()
    passing_marks = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.job.title

class CandidateTestAttempt(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE)
    aptitude_score = models.IntegerField(default=0)
    skill_score = models.IntegerField(default=0)
    coding_score = models.IntegerField(default=0)
    score = models.IntegerField()
    passed = models.BooleanField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.candidate.user.username} - {self.application.job.title}"