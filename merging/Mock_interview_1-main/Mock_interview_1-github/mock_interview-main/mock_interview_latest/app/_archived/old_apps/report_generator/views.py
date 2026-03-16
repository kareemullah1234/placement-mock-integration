from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.db.models import Avg, Count, Q
from django.utils import timezone
import csv
import json
from interview_system.models import Interview, InterviewResponse
from user_management.models import CustomUser
from .models import InterviewReport, SystemAnalytics
from .services import ReportService

@staff_member_required
def dashboard_stats(request):
    """Get dashboard statistics"""
    try:
        stats = {
            'totalStudents': CustomUser.objects.filter(is_student=True).count(),
            'completedInterviews': Interview.objects.filter(status='completed').count(),
            'pendingAnalysis': Interview.objects.filter(
                status='completed', 
                analysis_completed=False
            ).count(),
            'cheatingDetected': Interview.objects.filter(cheating_detected=True).count()
        }
        return JsonResponse(stats)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def analytics_data(request):
    """Get analytics data"""
    try:
        completed_interviews = Interview.objects.filter(
            status='completed',
            analysis_completed=True
        )
        
        total_count = completed_interviews.count()
        if total_count == 0:
            return JsonResponse({
                'averageScore': 0,
                'passRate': 0,
                'cheatingRate': 0
            })
        
        avg_score = completed_interviews.aggregate(
            avg=Avg('overall_score')
        )['avg'] or 0
        
        pass_count = completed_interviews.filter(overall_score__gte=60).count()
        cheating_count = completed_interviews.filter(cheating_detected=True).count()
        
        analytics = {
            'averageScore': round(avg_score, 1),
            'passRate': round((pass_count / total_count) * 100, 1),
            'cheatingRate': round((cheating_count / total_count) * 100, 1)
        }
        
        return JsonResponse(analytics)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def interview_report(request, interview_id):
    """Get detailed interview report"""
    try:
        interview = get_object_or_404(Interview, id=interview_id)
        
        # Check permissions
        if not (request.user == interview.student or request.user.is_staff):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        if not interview.analysis_completed:
            return JsonResponse({'error': 'Analysis not completed yet'}, status=400)
        
        # Generate or get existing report
        report_service = ReportService()
        report_data = report_service.generate_detailed_report(interview)
        
        if request.GET.get('format') == 'html':
            html_content = render_to_string('report_generator/interview_report.html', {
                'interview': interview,
                'report': report_data
            })
            return HttpResponse(html_content)
        
        return JsonResponse(report_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@staff_member_required
def export_reports(request):
    """Export reports in various formats"""
    try:
        format_type = request.GET.get('format', 'csv')
        
        interviews = Interview.objects.filter(
            status='completed',
            analysis_completed=True
        ).select_related('student')
        
        if format_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="interview_reports.csv"'
            
            writer = csv.writer(response)
            writer.writerow([
                'Student Name', 'Email', 'Interview Date', 'Overall Score', 
                'Grade', 'Cheating Detected', 'Cheating Confidence'
            ])
            
            for interview in interviews:
                writer.writerow([
                    interview.student.get_full_name(),
                    interview.student.email,
                    interview.created_at.strftime('%Y-%m-%d'),
                    interview.overall_score or 0,
                    get_grade(interview.overall_score or 0),
                    'Yes' if interview.cheating_detected else 'No',
                    f"{interview.cheating_confidence or 0:.1f}%"
                ])
            
            return response
            
        elif format_type == 'json':
            data = []
            for interview in interviews:
                data.append({
                    'student_name': interview.student.get_full_name(),
                    'email': interview.student.email,
                    'interview_date': interview.created_at.isoformat(),
                    'overall_score': interview.overall_score,
                    'grade': get_grade(interview.overall_score or 0),
                    'cheating_detected': interview.cheating_detected,
                    'cheating_confidence': interview.cheating_confidence
                })
            
            response = HttpResponse(
                json.dumps(data, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = 'attachment; filename="interview_reports.json"'
            return response
        
        return JsonResponse({'error': 'Unsupported format'}, status=400)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_grade(score):
    """Convert score to grade"""
    if score >= 90:
        return 'A+'
    elif score >= 80:
        return 'A'
    elif score >= 70:
        return 'B'
    elif score >= 60:
        return 'C'
    elif score >= 50:
        return 'D'
    else:
        return 'F'
