from django.contrib import admin
from .models import StudentProfile

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'user', 'phone_number', 'college', 'course', 'is_active')
    list_filter = ('is_active', 'college', 'course')
    search_fields = ('student_id', 'user__email', 'user__first_name', 'user__last_name')
