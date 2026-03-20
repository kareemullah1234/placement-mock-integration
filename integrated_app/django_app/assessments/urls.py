from django.urls import path
from . import views

app_name = "assessments"

urlpatterns = [
    path("instruction/<int:application_id>/", views.test_instruction, name="test_instruction"),
    path("start-test/<int:application_id>/", views.start_test, name="start_test"),
    path("submit-test/<int:application_id>/", views.submit_test, name="submit_test"),
    path("manage-test/<int:job_id>/", views.manage_test_config, name="manage_test_config"),
    path("run-code/", views.run_code_view, name="run_code"),
]