from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .services import AnalysisService

@login_required
def analysis_dashboard(request):
    """Analysis dashboard for admins"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    return render(request, 'video_analysis/dashboard.html')

@login_required
def trigger_analysis(request, interview_id):
    """Manually trigger analysis for an interview"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    
    try:
        analysis_service = AnalysisService()
        result = analysis_service.process_interview_analysis(interview_id)
        return JsonResponse({'success': True, 'result': result})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
