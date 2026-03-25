from django.db import models
from django.conf import settings

class CandidateProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=255, blank=True)
    differently_abled = models.BooleanField(default=False)
    
    user_type = models.CharField(max_length=50, blank=True) # College Students, Professional, Fresher
    domain = models.CharField(max_length=255, blank=True)
    college_name = models.CharField(max_length=255, blank=True)
    degree = models.CharField(max_length=255, blank=True)
    course_specialization = models.CharField(max_length=255, blank=True)
    graduating_year = models.IntegerField(null=True, blank=True)
    course_duration = models.IntegerField(null=True, blank=True)
    
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    backlogs = models.IntegerField(default=0)
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    extracted_skills = models.TextField(blank=True)
    skills = models.ManyToManyField("common.Skill", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username
    
