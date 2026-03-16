from django.urls import path
from . import views

urlpatterns = [ 
    path("profile/", views.candidate_profile, name="candidate_profile"),
    path("dashboard/", views.candidate_dashboard, name="candidate_dashboard"),
]