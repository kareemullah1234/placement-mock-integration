from django.conf import settings
from django.db import models

class StudentProfile(models.Model):
    PREFERENCE_CHOICES = [
        ('weekend', 'Preferably Weekend'),
        ('working_day', 'Working Day'),
    ]
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    college = models.CharField(max_length=200, blank=True)
    course = models.CharField(max_length=100, blank=True)
    year_of_study = models.IntegerField(null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    resume = models.FileField(upload_to='resumes/', blank=True)
    is_active = models.BooleanField(default=True)
    
    # New availability fields (matching your database schema)
    batch_id = models.CharField(max_length=100, default='', help_text="Complete Batch ID (not Project ID)")
    interview_preference = models.CharField(
        max_length=20, 
        choices=PREFERENCE_CHOICES, 
        default='',
        help_text="When will you be available for Mock Interview?"
    )
    availability_slots = models.JSONField(
        default=list, 
        help_text="Three preferred time slots with date, day, from_time, to_time"
    )
    availability_updated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.student_id}"
    
    def has_complete_availability(self):
        """Check if student has filled all required availability information"""
        return (
            self.batch_id and 
            self.interview_preference and 
            len(self.availability_slots) == 3 and
            all(
                slot.get('date') and 
                slot.get('day') and 
                slot.get('from_time') and 
                slot.get('to_time')
                for slot in self.availability_slots
            )
        )
    
    def get_availability_summary(self):
        """Get a formatted summary of availability"""
        if not self.has_complete_availability():
            return "Incomplete availability information"
        
        summary = f"Batch: {self.batch_id}, Preference: {self.get_interview_preference_display()}\n"
        for i, slot in enumerate(self.availability_slots, 1):
            summary += f"Slot {i}: {slot.get('day')} {slot.get('date')} ({slot.get('from_time')} - {slot.get('to_time')})\n"
        
        return summary.strip()
