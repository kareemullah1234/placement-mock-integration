from django.contrib import admin
from .models import Interview, InterviewResponse, InterviewFrames

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('student', 'attempt_number', 'status', 'overall_score', 'cheating_detected', 'created_at')
    list_filter = ('status', 'cheating_detected', 'analysis_completed', 'created_at')
    search_fields = ('student__email', 'student__first_name', 'student__last_name')
    readonly_fields = ('id', 'created_at')  # Remove 'updated_at' if not in the model

@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):
    list_display = ('interview', 'question_id', 'created_at')  # Removed content_score, fluency_score
    list_filter = ('created_at',)
    search_fields = ('interview__student__email', 'question_id')

@admin.register(InterviewFrames)
class InterviewFramesAdmin(admin.ModelAdmin):
    list_display = ('interview', 'total_frames')  # Removed suspicious_activity_count, multiple_faces_detected
    list_filter = ('created_at',)                 # Removed multiple_faces_detected
