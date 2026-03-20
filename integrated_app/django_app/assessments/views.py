from django.shortcuts import render, get_object_or_404, redirect
from .utils import generate_test_questions, evaluate_code_with_gemini
from .models import AptitudeTest, CandidateTestAttempt
from applications.models import Application
from companies.models import JobPost
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import json

@login_required
def test_instruction(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    
    # Ownership and status check
    if application.candidate.user != request.user:
        return redirect("candidate_dashboard")
    
    if CandidateTestAttempt.objects.filter(application=application).exists():
        messages.error(request, "You already attended this test.")
        return redirect("candidate_dashboard")

    return render(request, "assessments/instruction.html", {
        "application_id": application.id,
        "job": application.job
    })

@login_required
def start_test(request, application_id):
    application = get_object_or_404(Application, id=application_id)
    
    # Ownership check
    if application.candidate.user != request.user:
        return redirect("candidate_dashboard")

    if CandidateTestAttempt.objects.filter(application=application).exists():
        messages.error(request, "You already attended this test.")
        return redirect("candidate_dashboard")
    
    skills = [s.name for s in application.job.skills.all()]
    questions = generate_test_questions(skills)
    
    request.session["questions"] = questions
    
    return render(request, "assessments/test_page.html", {
        "questions": questions,
        "application_id": application.id
    })

@login_required
def submit_test(request, application_id):
    if request.method != "POST":
        return redirect("candidate_dashboard")

    application = get_object_or_404(Application, id=application_id)
    # Ownership check
    if application.candidate.user != request.user:
        return redirect("candidate_dashboard")

    questions = request.session.get("questions", {})
    aptitude_score = 0
    skill_score = 0
    coding_score = 0

    # ---------- Aptitude Section ----------
    for i, q in enumerate(questions.get("aptitude", [])):
        user_answer = request.POST.get(f"apt{i+1}")
        if user_answer == q["answer"]:
            aptitude_score += 1

    # ---------- Skill Section ----------
    for i, q in enumerate(questions.get("skills", [])):
        user_answer = request.POST.get(f"skill{i+1}")
        if user_answer == q["answer"]:
            skill_score += 1

    # ---------- Coding Section ----------
    for i, q in enumerate(questions.get("coding", [])):
        user_code = request.POST.get(f"code{i+1}")
        if user_code:
            try:
                score = evaluate_code_with_gemini(
                    q["question"],
                    user_code,
                    q.get("test_cases", [])
                )
                scaled_score = round((score / 10) * 5)
                coding_score += scaled_score
            except Exception as e:
                print(f"Error evaluating code: {e}")

    total_score = aptitude_score + skill_score + coding_score
    test = AptitudeTest.objects.filter(job=application.job).first()

    if not test:
        messages.error(request, "Test not available yet.")
        return redirect("candidate_dashboard")

    passed = total_score >= test.passing_marks

    CandidateTestAttempt.objects.create(
        application=application,
        aptitude_score=aptitude_score,
        skill_score=skill_score,
        coding_score=coding_score,
        score=total_score,
        passed=passed
    )

    if passed:
        application.status = "aptitude_passed"
    else:
        application.status = "aptitude_failed"
    application.save()

    if "questions" in request.session:
        del request.session["questions"]

    return render(request, "assessments/result.html", {
        "score": total_score,
        "passed": passed
    })

@login_required
def manage_test_config(request, job_id):
    from companies.models import CompanyProfile
    job = get_object_or_404(JobPost, id=job_id)
    
    # Ownership check
    try:
        company = CompanyProfile.objects.get(user=request.user)
        if job.company != company:
            return redirect("companies:company_dashboard")
    except CompanyProfile.DoesNotExist:
        return redirect("login")

    test, created = AptitudeTest.objects.get_or_create(job=job, defaults={
        'total_questions': 10,
        'total_marks': 100,
        'passing_marks': 40
    })

    if request.method == "POST":
        test.total_questions = request.POST.get("total_questions")
        test.total_marks = request.POST.get("total_marks")
        test.passing_marks = request.POST.get("passing_marks")
        test.save()
        messages.success(request, "Test configuration updated successfully.")
        return redirect("companies:company_dashboard")

    return render(request, "assessments/manage_test.html", {
        "job": job,
        "test": test
    })

from django.http import JsonResponse
from .utils import run_code, normalize_output
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def run_code_view(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        code = data.get("code")
        language = int(data.get("language"))
        test_cases = data.get("test_cases", [])

        while isinstance(test_cases, str):
            test_cases = json.loads(test_cases)

        function_name = data.get("function_name")
        if not function_name:
            questions = request.session.get("questions", {})
            if questions.get("coding"):
                function_name = questions["coding"][0].get("function_name")

        results = []
        passed = 0
        for i, tc in enumerate(test_cases):
            input_data = tc.get("input")
            expected_output = tc.get("output")
            output = run_code(code, language, json.dumps(input_data), function_name)

            if normalize_output(output) == normalize_output(expected_output):
                results.append(f"Testcase {i+1} Passed")
                passed += 1
            else:
                results.append(f"Testcase {i+1} Failed (Expected {expected_output} Got {output})")

        return JsonResponse({
            "results": results,
            "passed": passed,
            "total": len(test_cases)
        })
    except Exception as e:
        print("ERROR:", str(e))
        return JsonResponse({"error": str(e)}, status=500)