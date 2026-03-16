from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentProfile

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_student', 'is_admin', 'is_active')
    list_filter = ('is_student', 'is_admin', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('candidate_id', 'phone_number', 'is_student', 'is_admin')
        }),
    )

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'college', 'course', 'is_active')
    list_filter = ('is_active', 'college', 'course')
    search_fields = ('student_id', 'user__email', 'user__first_name', 'user__last_name')
