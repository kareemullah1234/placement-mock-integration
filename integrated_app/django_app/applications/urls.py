from django.urls import path
from . import views

app_name = "applications"

urlpatterns = [
    path("apply/<int:job_id>/", views.apply_job, name="apply_job"),
    path("choose-slot/<int:application_id>/", views.choose_test_slot, name="choose_test_slot"),
    path("job/<int:job_id>/", views.job_applicants, name="job_applicants"),
]
