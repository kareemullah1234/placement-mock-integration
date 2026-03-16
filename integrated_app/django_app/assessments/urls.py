from django.urls import path
from . import views

urlpatterns = [

path("start-test/<int:application_id>/", views.start_test, name="start_test"),

path("submit-test/<int:application_id>/", views.submit_test, name="submit_test"),

]