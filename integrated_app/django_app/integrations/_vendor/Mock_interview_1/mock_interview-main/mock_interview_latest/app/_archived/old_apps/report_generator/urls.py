from django.urls import path
from . import views

urlpatterns = [
    path('dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('analytics/', views.analytics_data, name='analytics_data'),
    path('interview/<uuid:interview_id>/', views.interview_report, name='interview_report'),
    path('export/', views.export_reports, name='export_reports'),
]
