from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from candidates.models import CandidateProfile
from companies.models import CompanyProfile, JobPost


User = get_user_model()

def admin_stats(request):

    data = {
        "candidates": CandidateProfile.objects.count(),
        "companies": CompanyProfile.objects.count(),
        "jobs": JobPost.objects.count()
    }

    return JsonResponse(data)

from django.http import JsonResponse
from candidates.models import CandidateProfile

def admin_users(request):

    profiles = CandidateProfile.objects.select_related("user")

    data = []

    for profile in profiles:

        data.append({
            "id": profile.user.id,
            "name": profile.user.first_name or profile.user.username,
            "email": profile.user.email,
            "phone": profile.phone,
            "resume": profile.resume.url if profile.resume else None
        })

    return JsonResponse({"users": data})