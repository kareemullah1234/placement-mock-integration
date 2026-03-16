from django import forms
from .models import CandidateProfile

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = CandidateProfile
        fields = ['phone', 'resume']   # Only these visible