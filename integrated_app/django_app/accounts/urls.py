from django.urls import path
from .views import register, CustomLoginView
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('register/', register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("redirect/", views.redirect_user, name="role_redirect"),
]