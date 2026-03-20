import os
import django
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlacementPortal.settings')
django.setup()

from django.contrib.auth import get_user_model
from companies.models import CompanyProfile, JobPost
from candidates.models import CandidateProfile

User = get_user_model()

def run_demo():
    print("=" * 60)
    print(">>> STARTING LIVE CANDIDATE DEMO")
    print("=" * 60)
    
    # Setup test data
    print("\n>>> STEP 1: Setting up environment...")
    User.objects.filter(username='cand_demo').delete()
    user = User.objects.create_user(username='cand_demo', email='cand@demo.com', password='password123', role='candidate')
    
    User.objects.filter(username='comp_demo').delete()
    comp_user = User.objects.create_user(username='comp_demo', email='comp@demo.com', password='password123', role='company')
    comp = CompanyProfile.objects.create(user=comp_user, company_name="Tech Corp", website="https://tech.corp")
    
    job = JobPost.objects.create(company=comp, title="Python Engineer", description="Need a python dev", location="Remote", salary=100000, is_active=True)
    job.required_skills = "python, django, sql"
    job.save()

    client = Client()
    
    login_success = client.login(username='cand_demo', password='password123')
    print(f"  [+] Candidate logged in: {login_success}")
    
    # 1. Update Profile
    print("\n>>> STEP 2: Candidate updating profile (Phone Number)...")
    response = client.post('/candidates/profile/', {'phone': '+91 9988776655'})
    print(f"  [+] Profile Update Response: {response.status_code} (302 means success redirect)")
    
    cand_profile = CandidateProfile.objects.get(user=user)
    print(f"  [+] Candidate Phone in DB: {cand_profile.phone}")
    
    # 2. View Dashboard
    print("\n>>> STEP 3: Candidate visits Dashboard...")
    response = client.get('/candidates/dashboard/')
    print(f"  [+] Dashboard Response: {response.status_code}")
    if response.status_code == 200:
        print("  [+] Template rendered successfully.")
        
    # 3. Apply to Job (Upload Resume)
    print("\n>>> STEP 4: Candidate uploading resume for job ID", job.id, "...")
    mock_resume = SimpleUploadedFile(
        "resume.pdf",
        b"This is a mock resume containing python, django, xml, and css.",
        content_type="application/pdf"
    )
    
    response = client.post(f'/candidates/upload-resume/{job.id}/', {'resume': mock_resume})
    print(f"  [+] Upload Resume Response: {response.status_code}")
    
    cand_profile.refresh_from_db()
    if cand_profile.resume:
        print(f"  [+] Resume saved to DB: {cand_profile.resume.name}")
        
    print("\n" + "=" * 60)
    print(">>> DEMO COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    run_demo()
