from django.contrib import admin
from .models import InterviewReport, SystemAnalytics

@admin.register(InterviewReport)
class InterviewReportAdmin(admin.ModelAdmin):
    list_display = ('interview', 'final_grade', 'technical_score', 'integrity_score', 'generated_at')
    list_filter = ('final_grade', 'generated_at')
    search_fields = ('interview__student__email', 'interview__student__first_name')
    readonly_fields = ('generated_at',)

@admin.register(SystemAnalytics)
class SystemAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_interviews', 'completed_interviews', 'average_score', 'cheating_incidents')
    list_filter = ('date',)
    ordering = ['-date']
