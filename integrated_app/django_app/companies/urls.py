from django.urls import path
from . import views

app_name = "companies"

urlpatterns = [
    path("create-job/", views.create_job, name="create_job"),
    path("jobs/", views.job_list, name="job_list"),
    path("my-jobs/", views.company_jobs, name="company_jobs"),
    path("dashboard/", views.company_dashboard, name="company_dashboard"),
    path("edit-job/<int:job_id>/", views.edit_job, name="edit_job"),
    path("profile/", views.company_profile, name="company_profile"),
    path("delete-job/<int:job_id>/", views.delete_job, name="delete_job"),
    path("job-applicants/<int:job_id>/", views.job_applicants, name="job_applicants"),
    path("allow-test/<int:application_id>/", views.allow_test, name="allow_test"),
]