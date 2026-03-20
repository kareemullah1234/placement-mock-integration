from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from candidates.models import CandidateProfile
from companies.models import CompanyProfile, JobPost
from applications.models import Application
from assessments.models import AptitudeTest, CandidateTestAttempt
import json

User = get_user_model()

class EndToEndAssessmentTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # 1. Setup Data
        self.company_user = User.objects.create_user(username='hr_e2e', email='hr@demo.com', password='pw', role='company')
        self.company_profile = CompanyProfile.objects.create(user=self.company_user, company_name='End2End Corp')
        self.job = JobPost.objects.create(company=self.company_profile, title='React Dev', salary=80000, is_active=True)
        self.apt_test = AptitudeTest.objects.create(job=self.job, total_questions=3, total_marks=30, passing_marks=15)
        
        self.candidate_user = User.objects.create_user(username='cand_e2e', email='cand@demo.com', password='pw', role='candidate')
        self.candidate_profile = CandidateProfile.objects.create(user=self.candidate_user)
        self.application = Application.objects.create(candidate=self.candidate_profile, job=self.job, status='test_scheduled')

    @patch('assessments.views.generate_test_questions')
    @patch('assessments.utils.requests.post')
    @patch('assessments.views.evaluate_code_with_gemini')
    def test_full_candidate_assessment_flow(self, mock_evaluate_code, mock_judge0_post, mock_gen_questions):
        """
        End-to-end test verifying a candidate starting the test, running code, and submitting correctly.
        """
        # STEP 1: Candidate Logs In
        self.client.login(username='cand_e2e', password='pw')

        # STEP 2: Candidate starts the test (Generates Questions)
        mock_questions = {
            'aptitude': [{'question': 'What is 2+2?', 'options': ['2', '3', '4', '5'], 'answer': '4'}],
            'skills': [{'question': 'Describe React?', 'options': ['UI', 'DB', 'OS', 'None'], 'answer': 'UI'}],
            'coding': [{
                'question': 'Write return 10',
                'function_name': 'get_ten',
                'example_input': '',
                'example_output': '10',
                'test_cases': [{'input': '', 'output': 10}]
            }]
        }
        mock_gen_questions.return_value = mock_questions
        
        start_url = reverse('assessments:start_test', args=[self.application.id])
        start_response = self.client.get(start_url)
        
        self.assertEqual(start_response.status_code, 200, "Should load the test page.")
        # Check if questions were saved to session properly
        self.assertEqual(self.client.session['questions']['aptitude'][0]['question'], 'What is 2+2?')

        # STEP 3: Candidate executes code in the browser using run-code API
        mock_response = MagicMock()
        mock_response.json.return_value = {"stdout": "10"}
        mock_judge0_post.return_value = mock_response

        run_code_url = reverse('assessments:run_code')
        payload = {
            'code': 'def get_ten(data):\n    return 10',
            'language': '71',
            'test_cases': json.dumps(mock_questions['coding'][0]['test_cases']),
            'function_name': 'get_ten'
        }
        
        run_code_response = self.client.post(
            run_code_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(run_code_response.status_code, 200)
        self.assertIn("Testcase 1 Passed", run_code_response.json()['results'][0])

        # STEP 4: Candidate submits the final assessment
        mock_evaluate_code.return_value = 10 # 10/10 from Gemini for code quality/logic
        
        submit_url = reverse('assessments:submit_test', args=[self.application.id])
        submit_payload = {
            'apt1': '4',          # Correct answer for 2+2
            'skill1': 'UI',       # Correct answer for React
            'code1': 'def get_ten(data):\n    return 10'
        }
        
        submit_response = self.client.post(submit_url, data=submit_payload)
        self.assertEqual(submit_response.status_code, 200)

        # STEP 5: Verify the Application Status was updated
        self.application.refresh_from_db()
        
        # Let's check the test attempt record
        attempt_exists = CandidateTestAttempt.objects.filter(application=self.application).exists()
        self.assertTrue(attempt_exists, "A test attempt record should be created.")
        
        attempt = CandidateTestAttempt.objects.get(application=self.application)
        
        # 1 apt point + 1 skill point + 5 scaled coding points = 7 total score, out of 30 marks...
        # Our passing marks is 15 so they will fail.
        self.assertFalse(attempt.passed, "Candidate should fail because score 7 < passing 15")
        self.assertEqual(self.application.status, 'aptitude_failed')
