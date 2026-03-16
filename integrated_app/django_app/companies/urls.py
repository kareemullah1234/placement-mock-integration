from django.urls import path
from . import views

urlpatterns = [
    path("create-job/", views.create_job, name="create_job"),
    path("jobs/", views.job_list, name="job_list"),
    path("my-jobs/", views.company_jobs, name="company_jobs"),
    path("dashboard/", views.company_dashboard, name="company_dashboard"),
    path("edit-job/<int:job_id>/", views.edit_job, name="edit_job"),
]