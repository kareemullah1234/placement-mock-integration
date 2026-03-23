from django.urls import path
from common import views

urlpatterns = [
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/stats/", views.admin_stats, name="admin_stats"),
    path("admin/users/", views.admin_users, name="admin_users"),
]