from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.analysis_dashboard, name='analysis_dashboard'),
    path('trigger/<uuid:interview_id>/', views.trigger_analysis, name='trigger_analysis'),
]
