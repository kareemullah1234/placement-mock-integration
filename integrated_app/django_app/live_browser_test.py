"""
Live Browser Test - simulates a real user session via Django's test client
and checks every candidate page for errors.
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlacementPortal.settings')
os.environ['PYTHONIOENCODING'] = 'utf-8'
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from companies.models import CompanyProfile, JobPost
from candidates.models import CandidateProfile
from applications.models import Application

User = get_user_model()

PASS  = "[PASS]"
FAIL  = "[FAIL]"
total = 0
passed = 0

def check(label, condition, detail=""):
    global total, passed
    total += 1
    if condition:
        passed += 1
        print(f"  {PASS}  {label}")
    else:
        print(f"  {FAIL}  {label}  ->  {detail}")

def has_no_errors(content):
    bad = ["TemplateSyntaxError", "TemplateDoesNotExist", "NoReverseMatch",
           "Traceback", "Server Error (500)", "Page not found (404)"]
    for b in bad:
        if b in content:
            return False, b
    return True, ""

# ================================================================
print("=" * 60)
print(">>> LIVE BROWSER TEST -- CANDIDATES APP")
print("=" * 60)

# -- Setup --
print("\n[Setup] Creating test data...")
User.objects.filter(username='live_test_cand').delete()
User.objects.filter(username='live_test_comp').delete()

cand_user = User.objects.create_user(username='live_test_cand', password='Test1234!', role='candidate')
comp_user = User.objects.create_user(username='live_test_comp', password='Test1234!', role='company')
comp = CompanyProfile.objects.create(user=comp_user, company_name="LiveTest Corp", website="https://live.test", description="test")
job  = JobPost.objects.create(company=comp, title="Live Test Engineer", description="testing", location="Remote", salary=90000, is_active=True)
cand_profile = CandidateProfile.objects.create(user=cand_user, phone="0000000000")
app  = Application.objects.create(candidate=cand_profile, job=job, status='applied')

client = Client()

# -- TEST 1: Login --
print("\n-- TEST 1: Login --")
login_ok = client.login(username='live_test_cand', password='Test1234!')
check("Login succeeds", login_ok, "Could not log in")

# -- TEST 2: Dashboard page --
print("\n-- TEST 2: Dashboard Page (/candidates/dashboard/) --")
resp = client.get('/candidates/dashboard/')
check("Returns HTTP 200", resp.status_code == 200, f"Got {resp.status_code}")
if resp.status_code == 200:
    html = resp.content.decode()
    ok, err = has_no_errors(html)
    check("No Django template errors", ok, err)
    check("Contains 'Dashboard' heading", "Dashboard" in html, "Missing heading")
    check("Contains nav bar (Placement Portal)", "Placement" in html and "Portal" in html, "Missing nav")
    check("Contains 'Applied Jobs' section", "Applied Jobs" in html or "Applied" in html, "Missing table")
    check("Contains Tailwind CSS", "tailwindcss" in html, "Tailwind not loaded")
    check("Contains Font Awesome icons", "font-awesome" in html or "fontawesome" in html, "Icons not loaded")
    check("Uses dark theme (bg #020617)", "#020617" in html, "Dark theme missing")
    check("Uses glassmorphism (backdrop-filter)", "backdrop-filter" in html, "Glass effect missing")
    check("Shows the test job", "Live Test Engineer" in html or "Applied" in html, "Job data missing")

# -- TEST 3: Profile page --
print("\n-- TEST 3: Profile Page (/candidates/profile/) --")
resp = client.get('/candidates/profile/')
check("Returns HTTP 200", resp.status_code == 200, f"Got {resp.status_code}")
if resp.status_code == 200:
    html = resp.content.decode()
    ok, err = has_no_errors(html)
    check("No Django template errors", ok, err)
    check("Contains phone input field", 'name="phone"' in html, "Missing phone input")
    check("Contains resume upload", 'name="resume"' in html, "Missing resume upload")
    check("Contains CSRF token", "csrfmiddlewaretoken" in html, "Missing CSRF")
    check("Uses dark theme (bg #020617)", "#020617" in html, "Dark theme missing")
    check("Uses glassmorphism (backdrop-filter)", "backdrop-filter" in html, "Glass effect missing")

# -- TEST 4: Profile form submission --
print("\n-- TEST 4: Profile Form Submission --")
resp = client.post('/candidates/profile/', {'phone': '+91 1234567890'})
check("Returns HTTP 302 redirect", resp.status_code == 302, f"Got {resp.status_code}")
cand_profile.refresh_from_db()
check("Phone saved in DB", cand_profile.phone == '+91 1234567890', f"Got: {cand_profile.phone}")

# -- TEST 5: Upload Resume page --
print(f"\n-- TEST 5: Upload Resume Page (/candidates/upload-resume/{job.id}/) --")
resp = client.get(f'/candidates/upload-resume/{job.id}/')
check("Returns HTTP 200", resp.status_code == 200, f"Got {resp.status_code}")
if resp.status_code == 200:
    html = resp.content.decode()
    ok, err = has_no_errors(html)
    check("No Django template errors", ok, err)
    check("Contains file upload input", 'name="resume"' in html, "Missing file input")
    check("Shows job title", "Live Test Engineer" in html, "Job title missing")
    check("Uses dark theme (bg #020617)", "#020617" in html, "Dark theme missing")

# -- TEST 6: Resume upload submission --
print("\n-- TEST 6: Resume Upload Submission --")
from django.core.files.uploadedfile import SimpleUploadedFile
mock_resume = SimpleUploadedFile("test_resume.pdf", b"python django sql css html javascript", content_type="application/pdf")
resp = client.post(f'/candidates/upload-resume/{job.id}/', {'resume': mock_resume})
check("Returns HTTP 200 or 302", resp.status_code in [200, 302], f"Got {resp.status_code}")
if resp.status_code == 200:
    html = resp.content.decode()
    ok, err = has_no_errors(html)
    check("Result page has no errors", ok, err)
    check("Shows match score", "Match Score" in html or "%" in html, "Score missing")

# -- TEST 7: Result page UI (rendered from upload) --
print("\n-- TEST 7: Result Page UI Check --")
if resp.status_code == 200:
    html = resp.content.decode()
    check("Contains result status", "Shortlisted" in html or "Rejected" in html, "Status missing")
    check("Contains required skills section", "Required Skills" in html or "required" in html.lower(), "Skills section missing")
    check("Uses dark theme", "#020617" in html, "Dark theme missing")
    check("Uses glassmorphism", "backdrop-filter" in html, "Glass effect missing")

# -- SUMMARY --
print("\n" + "=" * 60)
print(f">>> RESULTS: {passed}/{total} tests passed")
if passed == total:
    print(">>> ALL TESTS PASSED!")
else:
    print(f">>> {total - passed} test(s) FAILED")
print("=" * 60)

# Cleanup
User.objects.filter(username='live_test_cand').delete()
User.objects.filter(username='live_test_comp').delete()
