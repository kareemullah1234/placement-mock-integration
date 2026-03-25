from django.urls import path
from . import views

app_name = 'candidates'

urlpatterns = [ 
    path("profile/", views.candidate_profile, name="candidate_profile"),
    path("dashboard/", views.candidate_dashboard, name="candidate_dashboard"),
    path("dashboard-api/", views.dashboard_api, name="candidate_dashboard_api"),
    path('profile/update/', views.update_profile, name="update_profile"),
    path('profile/get/', views.get_profile, name="get_profile"),
    path('upload-resume/<int:job_id>/', views.upload_resume, name="upload_resume"),
    path('analysis/', views.resume_analysis, name="resume_analysis"),
]