from django.shortcuts import render, get_object_or_404, redirect
from .utils import generate_aptitude_questions
from .models import AptitudeTest
from applications.models import Application
from django.contrib import messages

def start_test(request, application_id):

    application = Application.objects.get(id=application_id)

    test = AptitudeTest.objects.get(job=application.job)

    questions = generate_aptitude_questions(application.job.title, test.total_questions)

    request.session["questions"] = questions

    return render(request, "assessments/test_page.html", {
        "questions": questions,
        "application_id": application_id
    })

from .models import CandidateTestAttempt
from applications.models import Application
from assessments.models import AptitudeTest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages


def submit_test(request, application_id):

    questions = request.session.get("questions", [])

    score = 0

    for i, q in enumerate(questions):
        user_answer = request.POST.get(f"q{i}")

        if user_answer == q["answer"]:
            score += 1

    application = get_object_or_404(Application, id=application_id)

    test = AptitudeTest.objects.filter(job=application.job).first()

    if not test:
        messages.error(request, "Test not available yet. Please wait.")
        return redirect("candidate_dashboard")

    passed = score >= test.passing_marks

    # Save test attempt
    CandidateTestAttempt.objects.create(
        application=application,
        score=score,
        passed=passed
    )

    # ✅ Update application status
    if passed:
        application.status = "aptitude_passed"
    else:
        application.status = "aptitude_failed"

    application.save()

    return render(request, "assessments/result.html", {
        "score": score,
        "passed": passed
    })