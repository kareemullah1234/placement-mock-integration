from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from candidates.models import CandidateProfile
from companies.models import JobPost
from .models import Application
from django.utils import timezone
from datetime import timedelta

@login_required
def apply_job(request, job_id):
    candidate = get_object_or_404(CandidateProfile, user=request.user)
    job = get_object_or_404(JobPost, id=job_id)
    
    if request.method == "POST":
        # Save Basic & User details to profile
        candidate.full_name = request.POST.get("full_name")
        candidate.phone = request.POST.get("phone")
        candidate.gender = request.POST.get("gender")
        candidate.location = request.POST.get("location")
        candidate.differently_abled = request.POST.get("differently_abled") == "Yes"
        
        candidate.user_type = request.POST.get("user_type")
        candidate.domain = request.POST.get("domain")
        candidate.college_name = request.POST.get("college_name")
        candidate.degree = request.POST.get("degree")
        candidate.course_specialization = request.POST.get("course_specialization")
        candidate.graduating_year = request.POST.get("graduating_year")
        candidate.course_duration = request.POST.get("course_duration")
        
        candidate.cgpa = request.POST.get("cgpa")
        candidate.backlogs = request.POST.get("backlogs") or 0
        candidate.save()

        # Create application
        application, created = Application.objects.get_or_create(
            candidate=candidate,
            job=job,
            defaults={'status': 'applied'}
        )
        return redirect("companies:job_list")

    return render(request, "applications/apply_job.html", {"job": job, "candidate": candidate})

@login_required
def choose_test_slot(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    
    # Ownership check
    if application.candidate.user != request.user:
        return redirect("candidate_dashboard")

    if request.method == "POST":
        slot = request.POST.get("slot")
        if slot == "10min":
            application.test_scheduled_at = timezone.now() + timedelta(minutes=10)
        elif slot == "1day":
            application.test_scheduled_at = timezone.now() + timedelta(days=1)
        elif slot == "2days":
            application.test_scheduled_at = timezone.now() + timedelta(days=2)
        elif slot == "now":
            application.test_scheduled_at = timezone.now()

        application.status = "test_scheduled"
        application.save()
        
        if slot == "now":
            return redirect("assessments:test_instruction", application_id=application.id)
        
        return redirect("candidate_dashboard")

    return render(request, "applications/choose_slot.html")

@login_required
def job_applicants(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    
    # Ownership check (job belongs to company of current user)
    # Check if user has a company profile and it matches the job
    try:
        from companies.models import CompanyProfile
        company = CompanyProfile.objects.get(user=request.user)
        if job.company != company:
             return redirect("companies:company_dashboard")
    except CompanyProfile.DoesNotExist:
        return redirect("login")

    applications = Application.objects.filter(job=job)
    return render(
        request,
        "applications/job_applicants.html",
        {
            "job": job,
            "applications": applications
        }
    )