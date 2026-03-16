from django.shortcuts import render, redirect
from .models import JobPost, CompanyProfile

def create_job(request):

    if not CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("job_list")
    
    company = CompanyProfile.objects.get(user=request.user)

    if request.method == "POST":

        title = request.POST.get("title")
        description = request.POST.get("description")
        skills = request.POST.get("skills")
        salary = request.POST.get("salary")


        JobPost.objects.create(
            company=company,
            title=title,
            description=description,
            required_skills=skills,
            salary=salary
        )

        return redirect("company_dashboard")

    return render(request, "companies/create_job.html")

from django.shortcuts import render, redirect
from candidates.models import CandidateProfile
from .models import JobPost


def job_list(request):

    candidate = CandidateProfile.objects.get(user=request.user)

    if not candidate.resume:
        return redirect("candidate_profile")

    # candidate skills
    candidate_skills = [
        skill.strip().lower()
        for skill in candidate.extracted_skills.split(",")
        if skill.strip()
    ]

    jobs = JobPost.objects.filter(is_active=True)

    matched_jobs = []

    for job in jobs:

        job_skills = [
            skill.strip().lower()
            for skill in job.required_skills.split(",")
        ]

        # check if ANY skill matches
        if set(candidate_skills) & set(job_skills):
            matched_jobs.append(job)

    print("Candidate Skills:", candidate_skills)

    return render(
        request,
        "companies/job_list.html",
        {"jobs": matched_jobs}
    )


from .models import JobPost, CompanyProfile

def company_jobs(request):
    
    if not CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("job_list")
    
    company = CompanyProfile.objects.get(user=request.user)

    jobs = JobPost.objects.filter(company=company)

    return render(request, "companies/company_jobs.html", {"jobs": jobs})

from companies.models import CompanyProfile
from django.shortcuts import redirect

def company_dashboard(request):

    if not CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("login")

    company = CompanyProfile.objects.get(user=request.user)

    jobs = JobPost.objects.filter(company=company)

    applications = Application.objects.filter(job__company=company)

    return render(
        request,
        "companies/dashboard.html",
        {
            "jobs": jobs,
            "applications": applications
        }
    )

from django.shortcuts import redirect
from applications.models import Application

def allow_test(request, application_id):

    app = Application.objects.get(id=application_id)

    app.status = "shortlisted"
    app.save()

    return redirect("company_dashboard")


from django.shortcuts import render, get_object_or_404, redirect
from .models import JobPost

def edit_job(request, job_id):

    job = get_object_or_404(JobPost, id=job_id)

    if request.method == "POST":

        job.title = request.POST.get("title")
        job.description = request.POST.get("description")
        job.required_skills = request.POST.get("skills")

        job.save()

        return redirect("company_dashboard")

    return render(request, "companies/edit_job.html", {"job": job})

from django.shortcuts import render, redirect
from .models import CompanyProfile

def company_profile(request):

    company = CompanyProfile.objects.get(user=request.user)

    if request.method == "POST":

        company.company_name = request.POST.get("company_name")
        company.website = request.POST.get("website")
        company.description = request.POST.get("description")
        company.location = request.POST.get("location")

        company.save()

        return redirect("company_dashboard")

    return render(request, "companies/company_profile.html", {"company": company})