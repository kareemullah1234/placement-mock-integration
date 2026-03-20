import os, sys, django, json
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PlacementPortal.settings')
os.environ['ALLOWED_HOSTS'] = '*'
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from candidates.models import CandidateProfile
from companies.models import CompanyProfile, JobPost
from applications.models import Application
from assessments.models import AptitudeTest, CandidateTestAttempt
from common.models import Skill

User = get_user_model()

print('\n' + '='*60)
print('>>> STARTING LIVE CANDIDATE ASSESSMENT DEMO')
print('='*60 + '\n')

print('>>> STEP 1: Setting up environment (Mock Data)...')
cand_user, _ = User.objects.get_or_create(username='demo_student', email='demo@gmail.com', defaults={'role': 'candidate'})
cand_user.set_password('demo123')
cand_user.save()
cand_profile, _ = CandidateProfile.objects.get_or_create(user=cand_user)

comp_user, _ = User.objects.get_or_create(username='demo_hr', email='hr@demo.com', defaults={'role': 'company'})
comp_user.set_password('demo123')
comp_user.save()
comp_profile, _ = CompanyProfile.objects.get_or_create(user=comp_user, defaults={'company_name': 'DemoCorp'})

job, _ = JobPost.objects.get_or_create(company=comp_profile, title='Junior Python Dev', defaults={'description': 'Demo', 'location': 'Remote', 'salary': 100, 'is_active': True})
app, _ = Application.objects.get_or_create(candidate=cand_profile, job=job, defaults={'status': 'test_scheduled'})
test, _ = AptitudeTest.objects.get_or_create(job=job, defaults={'total_questions': 3, 'total_marks': 30, 'passing_marks': 15})

# Clean previous attempts
CandidateTestAttempt.objects.filter(application=app).delete()
# Ensure app status is ready to take test
app.status = 'test_scheduled'
app.save()

print('  [+] Candidate (demo_student), Company, Job, and Test Config ready.')
print(f'  [+] Application ID: {app.id}')

c = Client()
c.login(username='demo_student', password='demo123')
print('  [+] Candidate logged in.\n')

print('>>> STEP 2: Candidate clicks "Start Test"...')
fake_questions = {
    'aptitude': [{'question': 'What is 5 + 5?', 'options': ['5', '10', '15', '20'], 'answer': '10'}],
    'skills': [{'question': 'What does HTML stand for?', 'options': ['Hyper Text', 'Hyperlink', 'None', 'Both'], 'answer': 'Hyper Text'}],
    'communication': [{'question': 'Why do you want to join us?'}],
    'coding': [{
        'question': 'Write a function add10(n) that returns n+10.',
        'function_name': 'add10',
        'example_input': '5',
        'example_output': '15',
        'test_cases': [{'input': 5, 'output': 15}, {'input': 0, 'output': 10}]
    }]
}

with patch('assessments.views.generate_test_questions', return_value=fake_questions):
    url = f'/assessments/start-test/{app.id}/'
    r = c.get(url)
    print(f'  [+] GET {url} -> Status {r.status_code}')
    print('  [+] AI (Mocked) generated questions successfully.')
    print('  [+] Test session initialized in browser.\n')

print('>>> STEP 3: Candidate is typing code in the live editor...')
user_code = '''
def add10(n):
    return n + 10
'''
print('  [+] Candidate wrote code:')
for line in user_code.strip().split('\n'):
    print(f'      {line}')
print('')

print('>>> STEP 4: Candidate clicks "Run Code"...')
with patch('assessments.utils.requests.post') as mock_post:
    mock_response = patch('requests.Response').start()
    mock_response.json.return_value = {"stdout": "15"}
    mock_post.return_value = mock_response
    
    url = '/assessments/run-code/'
    payload = {
        'code': user_code,
        'language': '71',
        'test_cases': json.dumps(fake_questions['coding'][0]['test_cases']),
        'function_name': 'add10'
    }
    r = c.post(url, data=json.dumps(payload), content_type='application/json')
    res = r.json()
    print(f'  [+] POST {url} -> Status {r.status_code}')
    print(f'  [+] Judge0 Results:')
    for result in res.get('results', []):
        print(f'      - {result}')
    print(f'  [+] Live Execution Passed: {res.get("passed")}/{res.get("total")}\n')


print('>>> STEP 5: Candidate submits the entire assessment...')
with patch('assessments.views.evaluate_code_with_gemini', return_value=10):
    url = f'/assessments/submit-test/{app.id}/'
    payload = {
        'apt1': '10',
        'skill1': 'Hyper Text',
        'comm1': 'I love Python.',
        'code1': user_code
    }
    r = c.post(url, data=payload)
    print(f'  [+] POST {url} -> Status {r.status_code}')

print('\n>>> STEP 6: Reviewing Application Status...')
app.refresh_from_db()
try:
    attempt = CandidateTestAttempt.objects.get(application=app)
    print(f'  [+] Assessment Total Score: {attempt.score}')
    print(f'  [+] Assessment Passed: {attempt.passed}')
    print(f'  [+] Final Application Status: {app.status}\n')
except Exception as e:
    print('  [-] Failed to fetch attempt:', e)

print('='*60)
print('>>> DEMO COMPLETED SUCCESSFULLY')
print('='*60)
