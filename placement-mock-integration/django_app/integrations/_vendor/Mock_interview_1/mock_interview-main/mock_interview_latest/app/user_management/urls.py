from django.urls import path
# from django.views.generic import TemplateView
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Debug endpoint (temporary for CSRF troubleshooting)
    path('debug-headers/', views.debug_headers, name='debug_headers'),
    
    # path('video-debug/', TemplateView.as_view(template_name='user_management/video_debug.html'), name='video_debug'),

    # API endpoints for admin dashboard
    path('api/students/', views.get_students_list, name='get_students_list'),
    path('api/interviews/', views.get_interviews_list, name='get_interviews_list'),
    path('api/interviews/<uuid:interview_id>/approve/', views.approve_interview, name='approve_interview'),
    path('api/interviews/<uuid:interview_id>/reject/', views.reject_interview, name='reject_interview'),
    path('api/interviews/<uuid:interview_id>/delete/', views.delete_interview, name='delete_interview'),
    path('api/students/<int:student_id>/toggle-status/', views.toggle_student_status, name='toggle_student_status'),
    path('api/students/<int:student_id>/delete/', views.delete_student, name='delete_student'),

    # Add this line to your existing urlpatterns list in user_management/urls.py
    path('api/check-availability/', views.check_availability_status, name='check_availability_status'),
    
    # API endpoints for student dashboard
    path('api/update-profile/', views.update_profile, name='update_profile'),
    path('api/all-interviews/', views.get_all_interviews, name='get_all_interviews'),
    
    # Authentication API endpoints
    path('api/login/', views.api_login, name='api_login'),
    path('api/register/', views.api_register, name='api_register'),
]
