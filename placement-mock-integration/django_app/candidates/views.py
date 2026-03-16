from django.shortcuts import render, get_object_or_404, redirect
from .models import CandidateProfile
from companies.models import JobPost
from .utils import extract_text_from_resume
from applications.models import Application
from companies.models import CompanyProfile

def upload_resume(request, job_id):

    if CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("company_jobs")
    
    job = JobPost.objects.get(id=job_id)
    candidate, created = CandidateProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":

        resume_file = request.FILES['resume']

        # save resume file
        candidate.resume = resume_file

        # extract resume text
        resume_text = extract_text_from_resume(resume_file)

        # required skills from job
        job_skills = [skill.strip().lower() for skill in job.required_skills.split(",")]

        matched_skills = []

        for skill in job_skills:
            if skill in resume_text:
                matched_skills.append(skill)
        total_skills = len(job_skills)
        matched_count = len(matched_skills)

        match_score = (matched_count / total_skills) * 100

        if match_score >= 50:
            application, created = Application.objects.get_or_create(
                candidate=candidate,
                job=job
            )
            status = "Shortlisted"
            return redirect("start_test", application_id=application.id)
        else:
            status = "Rejected"
        # save extracted skills
        candidate.extracted_skills = ", ".join(matched_skills)

        # save everything
        candidate.save()

        return render(request, "candidates/result.html", {
            "required_skills": job_skills,
            "matched_skills": matched_skills,
            "match_score": round(match_score, 2),
            "status": status
        })

    return render(request, "candidates/upload_resume.html")

from django.shortcuts import render, redirect
from .models import CandidateProfile
from .utils import extract_text_from_resume, extract_skills_from_resume


def candidate_profile(request):

    candidate = CandidateProfile.objects.get(user=request.user)

    if request.method == "POST":

        resume = request.FILES.get("resume")

        if resume:

            candidate.resume = resume

            text = extract_text_from_resume(resume).lower()

            print("RESUME TEXT:", text)

            skills = extract_skills_from_resume(text)

            print("EXTRACTED SKILLS:", skills)

            candidate.extracted_skills = skills

            candidate.save()

            return redirect("candidate_dashboard")

    return render(request, "candidates/profile.html", {"candidate": candidate})

from django.shortcuts import render
from applications.models import Application
from .models import CandidateProfile
from django.utils import timezone

def candidate_dashboard(request):

    applications = Application.objects.filter(candidate__user=request.user)

    return render(
        request,
        "candidates/dashboard.html",
        {
            "applications": applications,
            "now": timezone.now()
        }
    )