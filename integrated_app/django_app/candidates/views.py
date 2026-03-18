from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import CandidateProfile
from companies.models import JobPost, CompanyProfile
from .utils import extract_text_from_resume, extract_skills_from_resume
from applications.models import Application
from assessments.models import CandidateTestAttempt
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from common.models import Skill
from django.contrib.auth import get_user_model
from interviews.models import Interview

User = get_user_model()

@login_required
def upload_resume(request, job_id):
    if CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("companies:company_jobs")
    
    job = get_object_or_404(JobPost, id=job_id)
    candidate, created = CandidateProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        resume_file = request.FILES.get('resume')
        if not resume_file:
             return render(request, "candidates/upload_resume.html", {"error": "Please upload a resume"})

        candidate.resume = resume_file
        resume_text = extract_text_from_resume(resume_file).lower()
        
        # job.required_skills is a text field in some versions, let's be safe
        required_skills_str = getattr(job, 'required_skills', '')
        job_skills = [skill.strip().lower() for skill in required_skills_str.split(",") if skill.strip()]

        matched_skills = []
        for skill in job_skills:
            if skill in resume_text:
                matched_skills.append(skill)
        
        total_skills = len(job_skills)
        matched_count = len(matched_skills)
        match_score = (matched_count / total_skills) * 100 if total_skills > 0 else 100

        if match_score >= 50:
            application, created = Application.objects.get_or_create(candidate=candidate, job=job)
            status = "Shortlisted"
            candidate.save()
            return redirect("assessments:start_test", application_id=application.id)
        else:
            status = "Rejected"

        for skill in matched_skills:
            skill_obj, created = Skill.objects.get_or_create(name=skill)
            candidate.skills.add(skill_obj)

        candidate.save()

        return render(request, "candidates/result.html", {
            "required_skills": job_skills,
            "matched_skills": matched_skills,
            "match_score": round(match_score, 2),
            "status": status
        })

    return render(request, "candidates/upload_resume.html")

@login_required
def candidate_profile(request):
    candidate, created = CandidateProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        candidate.phone = request.POST.get("phone")
        resume = request.FILES.get("resume")
        if resume:
            candidate.resume = resume
            text = extract_text_from_resume(resume).lower()
            skills = extract_skills_from_resume(text)
            skills_list = [s.strip().lower() for s in skills.split(",") if s.strip()]
            candidate.skills.clear()
            for skill in skills_list:
                skill_obj, created = Skill.objects.get_or_create(name=skill)
                candidate.skills.add(skill_obj)
            candidate.extracted_skills = ",".join(skills_list)
        candidate.save()
        return redirect("candidate_dashboard")

    return render(request, "candidates/profile.html", {"candidate": candidate})

@login_required
def candidate_dashboard(request):
    candidate = get_object_or_404(CandidateProfile, user=request.user)
    applications = Application.objects.filter(candidate=candidate)
    attempts = CandidateTestAttempt.objects.filter(application__candidate=candidate)
    attempted_ids = attempts.values_list("application_id", flat=True)

    # Fetch interviews for this candidate
    interviews = Interview.objects.filter(student=request.user).order_by('-created_at')

    for app in applications:
        app.test_attempted = app.id in attempted_ids

    return render(request, "candidates/dashboard.html", {
        "applications": applications,
        "attempted_ids": attempted_ids,
        "interviews": interviews,
        "now": timezone.now()
    })

@login_required
def dashboard_api(request):
    """API for candidate dashboard data including applications and interviews"""
    candidate = get_object_or_404(CandidateProfile, user=request.user)
    applications = Application.objects.filter(candidate=candidate)
    interviews = Interview.objects.filter(student=request.user).order_by('-created_at')
    
    app_data = []
    for app in applications:
        app_data.append({
            "id": app.id,
            "job_title": app.job.title,
            "company": app.job.company.company_name,
            "status": app.status
        })
    
    interview_data = []
    for interview in interviews:
        interview_data.append({
            "id": interview.id,
            "status": interview.status,
            "status_display": interview.get_status_display(),
            "scheduled_at": interview.scheduled_at.isoformat() if interview.scheduled_at else None,
            "expires_at": interview.expires_at.isoformat() if interview.expires_at else None
        })
        
    return JsonResponse({
        "applications": app_data,
        "interviews": interview_data,
        "user": {
            "id": request.user.id,
            "username": request.user.username,
            "name": request.user.get_full_name()
        }
    })

@csrf_exempt
def update_profile(request):
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        if not user_id or user_id == "null":
            return JsonResponse({"error":"Invalid user_id"}, status=400)
        
        try:
            profile = CandidateProfile.objects.get(user_id=user_id)
        except CandidateProfile.DoesNotExist:
            return JsonResponse({"error":"Profile not found"}, status=404)

        profile.phone = request.POST.get("phone", "")
        if request.FILES.get("resume"):
            profile.resume = request.FILES["resume"]
        profile.save()
        return JsonResponse({"message": "Profile updated"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def get_profile(request):
    user_id = request.GET.get("user_id")
    if not user_id:
        return JsonResponse({"error": "Missing user_id"}, status=400)
    try:
        user = User.objects.get(id=user_id)
        profile = CandidateProfile.objects.get(user=user)
    except (User.DoesNotExist, CandidateProfile.DoesNotExist):
        return JsonResponse({"error": "User or Profile not found"}, status=404)

    data = {
        "name": user.first_name or user.username,
        "email": user.email,
        "phone": profile.phone,
        "resume": profile.resume.url if profile.resume else None
    }
    return JsonResponse(data)