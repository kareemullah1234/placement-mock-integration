from django.shortcuts import render

from django.shortcuts import redirect, get_object_or_404
from candidates.models import CandidateProfile
from companies.models import JobPost
from .models import Application

def apply_job(request, job_id):

    candidate = get_object_or_404(CandidateProfile, user=request.user)

    job = get_object_or_404(JobPost, id=job_id)
    
    application = Application.objects.create(
        candidate=candidate,
        job=job,
        status="applied"
    )

    return redirect("choose_test_slot", application_id=application.id)


from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta


def choose_test_slot(request, application_id):

    application = Application.objects.get(id=application_id)

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

        return redirect("candidate_dashboard")

    return render(request, "applications/choose_slot.html")

from django.shortcuts import render
from .models import Application
from companies.models import JobPost

def job_applicants(request, job_id):

    job = JobPost.objects.get(id=job_id)

    applications = Application.objects.filter(job=job)

    return render(
        request,
        "applications/job_applicants.html",
        {
            "job": job,
            "applications": applications
        }
    )