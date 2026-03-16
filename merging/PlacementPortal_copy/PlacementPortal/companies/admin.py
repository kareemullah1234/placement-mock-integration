from django.contrib import admin
from .models import CompanyProfile, JobPost
# Register your models here.
admin.site.register(CompanyProfile)
admin.site.register(JobPost)