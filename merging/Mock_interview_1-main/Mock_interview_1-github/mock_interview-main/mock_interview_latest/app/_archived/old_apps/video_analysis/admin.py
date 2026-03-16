from django.contrib import admin
from .models import AnalysisResult

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('interview', 'final_score', 'grade', 'cv_score', 'transcript_score', 'processed_at')
    list_filter = ('grade', 'processed_at')
    search_fields = ('interview__student__email', 'interview__student__first_name')
    readonly_fields = ('processed_at',)

    # Additional customizations can be added here if needed
