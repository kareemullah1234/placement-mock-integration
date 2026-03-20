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
    
    application, created = Application.objects.get_or_create(
        candidate=candidate,
        job=job,
        defaults={'status': 'applied'}
    )
    return redirect("applications:choose_test_slot", application_id=application.id)

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