from django.shortcuts import render, get_object_or_404, redirect
from .utils import generate_test_questions, evaluate_code_with_gemini
from .models import AptitudeTest
from applications.models import Application
from django.contrib import messages
import json

def start_test(request, application_id):

    application = get_object_or_404(Application, id=application_id)

    
    from assessments.models import CandidateTestAttempt

    if CandidateTestAttempt.objects.filter(application=application).exists():
        messages.error(request, "You already attended this test.")
        return redirect("candidate_dashboard")
    
    skills = [s.name for s in application.job.skills.all()]

    questions = generate_test_questions(skills)
    print("GENERATED QUESTIONS:", questions)

    request.session["questions"] = questions
    
    return render(request, "assessments/test_page.html", {
        "questions": questions,
        "application_id": application.id
    })

from .models import CandidateTestAttempt
from applications.models import Application
from assessments.models import AptitudeTest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages


def submit_test(request, application_id):
    print("SUBMIT TEST VIEW CALLED")
    if request.method != "POST":
        return redirect("candidate_dashboard")

    if not application_id:
        application_id = request.POST.get("application_id")

    application = get_object_or_404(Application, id=application_id)

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
            score = evaluate_code_with_gemini(
                q["question"],
                user_code,
                q.get("test_cases", [])
            )
            scaled_score = round((score / 10) * 5)
            coding_score += scaled_score

    # ---------- Total Score ----------
    total_score = aptitude_score + skill_score + coding_score

    # ---------- Get Test Config ----------
    test = AptitudeTest.objects.filter(job=application.job).first()

    if not test:
        messages.error(request, "Test not available yet.")
        return redirect("candidate_dashboard")

    passed = total_score >= test.passing_marks

    # ---------- Save Attempt ----------
    CandidateTestAttempt.objects.create(
        application=application,
        aptitude_score=aptitude_score,
        skill_score=skill_score,
        coding_score=coding_score,
        score=total_score,
        passed=passed
    )

    # ---------- Update Application Status ----------
    if passed:
        application.status = "aptitude_passed"
    else:
        application.status = "aptitude_failed"

    application.save()

    # clear session
    if "questions" in request.session:
        del request.session["questions"]

    return render(request, "assessments/result.html", {
        "score": total_score,
        "passed": passed
    })


import json
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

        print("LANGUAGE RECEIVED:", language)

        test_cases = data.get("test_cases", [])

        print("TEST CASES BEFORE PARSING:", test_cases)

        # convert string testcases to list
        while isinstance(test_cases, str):
            test_cases = json.loads(test_cases)

        print("TEST CASES RECEIVED:", test_cases)

        # Get function_name from data or session
        function_name = data.get("function_name")
        if not function_name:
            questions = request.session.get("questions", {})
            if questions.get("coding"):
                function_name = questions["coding"][0].get("function_name")

        print("FUNCTION NAME FROM SESSION:", function_name)

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
                results.append(
                    f"Testcase {i+1} Failed (Expected {expected_output} Got {output})"
                )

        print("RESULTS:", results)

        return JsonResponse({
            "results": results,
            "passed": passed,
            "total": len(test_cases)
        })

    except Exception as e:
        print("ERROR:", str(e))
        return JsonResponse({"error": str(e)}, status=500)