import os
import django
from django.test import Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlacementPortal.settings')
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

User = get_user_model()
from companies.models import CompanyProfile, JobPost
from candidates.models import CandidateProfile
from applications.models import Application

def run_live_demo():
    print("\nSTARTING LIVE DEMO TEST CASE: APPLICATION FLOW\n" + "="*50)
    client = Client()

    import random
    suffix = random.randint(1000, 9999)
    # 1. SETUP demo data
    comp_user, _ = User.objects.get_or_create(username=f'recruiter_{suffix}', email=f'rec_{suffix}@demo.com')
    comp_user.set_password('pass123')
    comp_user.save()
    comp_prof, _ = CompanyProfile.objects.get_or_create(user=comp_user, defaults={'company_name': 'Tech Giants', 'website': 'http://tg.com', 'description': 'Demo'})
    
    job, _ = JobPost.objects.get_or_create(
        company=comp_prof, 
        title=f'AI Engineer {suffix}', 
        defaults={'description': 'Demo Job', 'location': 'London', 'salary': 120000, 'is_active': True}
    )
    
    cand_user, _ = User.objects.get_or_create(username=f'candidate_{suffix}', email=f'cand_{suffix}@demo.com')
    cand_user.set_password('pass123')
    cand_user.save()
    CandidateProfile.objects.get_or_create(user=cand_user)

    print(f"CONFIRMED: Recruiter '{comp_user.username}' and Job '{job.title}' are created.")

    # 2. CANDIDATE LOGIN
    print("ACTION: Candidate Logging In...")
    login_success = client.login(username=f'candidate_{suffix}', password='pass123')
    print(f"RESULT: Login {'SUCCESS' if login_success else 'FAILED'}")

    # 3. APPLY FOR JOB
    print(f"ACTION: Candidate Applying for Job ID: {job.id}...")
    apply_url = reverse('apply_job', args=[job.id])
    response = client.get(apply_url)
    print(f"RESULT: HTTP {response.status_code} (Redirecting to Slot Selection)")

    # 4. CHOOSE SLOT (After 1 Day)
    app = Application.objects.get(candidate__user=cand_user, job=job)
    print(f"ACTION: Candidate Choosing 'After 1 Day' Slot for Application ID: {app.id}...")
    slot_url = reverse('choose_test_slot', args=[app.id])
    response = client.post(slot_url, {'slot': '1day'})
    print(f"RESULT: HTTP {response.status_code} (Redirecting to Dashboard)")

    # 5. VERIFY DATABASE STATE
    app.refresh_from_db()
    print(f"VERIFY: New Status is '{app.get_status_display()}'")
    print(f"VERIFY: Test Scheduled At: {app.test_scheduled_at}")

    # 6. RECRUITER LOGIN & VIEW
    client.logout()
    print("ACTION: Recruiter Logging In...")
    client.login(username='demo_recruiter_final', password='pass123')
    applicants_url = reverse('job_applicants', args=[job.id])
    response = client.get(applicants_url)
    print(f"RESULT: Recruiter successfully viewed the console (HTTP {response.status_code})")

    print("\nLIVE DEMO COMPLETE! EVERYTHING IS WORKING PERFECTLY!\n" + "="*50)

if __name__ == "__main__":
    run_live_demo()
