from django.urls import path
from . import views

urlpatterns = [
    path('api/list/', views.get_questions_list, name='get_questions_list'),
    path('api/<str:folder>/<str:filename>/', views.get_question_audio, name='get_question_audio'),
    # Additional paths can be added here if needed
]
