from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import CompanyProfile, JobPost, Skill
from applications.models import Application
from candidates.models import CandidateProfile
from assessments.models import CandidateTestAttempt
from django.utils import timezone

@login_required
def create_job(request):
    if not CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("companies:job_list")
    
    company = CompanyProfile.objects.get(user=request.user)

    if request.method == "POST":
        title = request.POST.get("title", "")
        if not title:
            return render(request, "companies/create_job.html", {"error": "Title is required"})

        job, created = JobPost.objects.get_or_create(
            company=company,
            title = title,
            description = request.POST.get("description", ""),
            location=request.POST.get("location", ""),
            salary = request.POST.get("salary") or 0,
            is_active=True
        )
        skills_input = request.POST.get("skills")
        if skills_input:
            skills_list = [s.strip().lower() for s in skills_input.split(",")]
            for skill in skills_list:
                skill_obj, created = Skill.objects.get_or_create(name=skill)
                job.skills.add(skill_obj)
        job.save()
        return redirect("companies:company_dashboard")

    return render(request, "companies/create_job.html")

def job_list(request):
    jobs = JobPost.objects.filter(is_active=True).distinct()
    applied_job_ids = []
    if request.user.is_authenticated:
        try:
            candidate = CandidateProfile.objects.get(user=request.user)
            applied_job_ids = Application.objects.filter(candidate=candidate).values_list('job_id', flat=True)
        except CandidateProfile.DoesNotExist:
            pass
            
    return render(
        request,
        "companies/job_list.html",
        {
            "jobs": jobs,
            "applied_job_ids": applied_job_ids
        }
    )

@login_required
def company_jobs(request):
    if not CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("job_list")
    
    company = CompanyProfile.objects.get(user=request.user)
    jobs = JobPost.objects.filter(company=company)
    return render(request, "companies/company_jobs.html", {"jobs": jobs})

@login_required
def company_profile(request):
    company, created = CompanyProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        company.company_name = request.POST.get("company_name")
        company.website = request.POST.get("website")
        company.description = request.POST.get("description")
        company.save()
        return redirect("companies:company_dashboard")

    return render(request, "companies/company_profile.html", {"company": company})

@login_required
def company_dashboard(request):
    if not CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("login")
    
    company = CompanyProfile.objects.get(user=request.user)
    jobs = JobPost.objects.filter(company=company)
    applications = Application.objects.filter(job__company=company)
    
    for job in jobs:
        job.applicant_count = Application.objects.filter(job=job).count()

    attempts = CandidateTestAttempt.objects.filter(application__job__company=company)

    if not company.company_name:
        return redirect("companies:company_profile")
    
    return render(
        request,
        "companies/dashboard.html",
        {
            "jobs": jobs,
            "applications": applications,
            "attempts": attempts
        }
    )

@login_required
def allow_test(request, application_id):
    app = get_object_or_404(Application, id=application_id)
    if app.job.company.user != request.user:
        return redirect("companies:company_dashboard")

    app.status = "test_allowed"
    app.save()
    return redirect("companies:company_dashboard")

@login_required
def edit_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    if job.company.user != request.user:
        return redirect("companies:company_dashboard")

    if request.method == "POST":
        job.title = request.POST.get("title")
        job.description = request.POST.get("description")
        job.location = request.POST.get("location")
        job.salary = request.POST.get("salary")
        job.save()
        return redirect("companies:company_dashboard")

    return render(request, "companies/edit_job.html", {"job": job})

@login_required
def delete_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    if job.company.user == request.user:
        job.delete()
    return redirect("companies:company_dashboard")

@login_required
def job_applicants(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    if job.company.user != request.user:
         return redirect("companies:company_dashboard")
         
    applications = Application.objects.filter(job=job)
    attempts = CandidateTestAttempt.objects.filter(application__in=applications)
    return render(
        request,
        "companies/job_applicants.html",
        {
            "job": job,
            "applications": applications,
            "attempts": attempts
        }
    )