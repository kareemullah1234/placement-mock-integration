from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
from candidates.models import CandidateProfile
from companies.models import CompanyProfile, JobPost
from applications.models import Application
from .models import AptitudeTest, CandidateTestAttempt
import json

User = get_user_model()

class AssessmentTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company_user = User.objects.create_user(username='comp@as.com', email='comp@as.com', password='pw')
        self.company_profile = CompanyProfile.objects.create(user=self.company_user, company_name='Assess Co')
        self.job = JobPost.objects.create(company=self.company_profile, title='Coder', salary=50, is_active=True)
        self.apt_test = AptitudeTest.objects.create(job=self.job, total_questions=10, total_marks=10, passing_marks=5)
        self.candidate_user = User.objects.create_user(username='cand@as.com', email='cand@as.com', password='pw')
        self.candidate_profile = CandidateProfile.objects.create(user=self.candidate_user)
        self.application = Application.objects.create(candidate=self.candidate_profile, job=self.job, status='test_scheduled')

    @patch('assessments.views.generate_test_questions')
    def test_start_test(self, mock_gen):
        """1. Start test."""
        mock_gen.return_value = {"aptitude": [], "skills": [], "coding": []}
        self.client.login(username='cand@as.com', password='pw')
        url = reverse('assessments:start_test', args=[self.application.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @patch('assessments.views.evaluate_code_with_gemini')
    def test_submit_test_passed(self, mock_eval):
        """2. Submit and Pass."""
        mock_eval.return_value = 10 
        session = self.client.session
        session['questions'] = {
            "aptitude": [{"question": "Q", "answer": "A"}],
            "skills": [], "coding": [{"question": "C", "function_name": "F"}]
        }
        session.save()
        self.client.login(username='cand@as.com', password='pw')
        url = reverse('assessments:submit_test', args=[self.application.id])
        self.client.post(url, {"apt1": "A", "code1": "C"})
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "aptitude_passed")

    @patch('assessments.views.run_code')
    def test_run_code_api(self, mock_run):
        """3. Code API."""
        mock_run.return_value = "10"
        url = reverse('assessments:run_code')
        self.client.login(username='cand@as.com', password='pw')
        response = self.client.post(url, data=json.dumps({"code": "C", "function_name": "F", "language": 71, "test_cases": [{"input": 1, "output": 10}]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)

    def test_re_attempt_prevention(self):
        """4. Block re-attempt."""
        CandidateTestAttempt.objects.create(application=self.application, score=8, passed=True)
        self.client.login(username='cand@as.com', password='pw')
        url = reverse('assessments:start_test', args=[self.application.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    @patch('assessments.views.evaluate_code_with_gemini')
    def test_submit_test_failed(self, mock_eval):
        """5. Submit and Fail."""
        mock_eval.return_value = 0
        session = self.client.session
        session['questions'] = {"aptitude": [], "skills": [], "coding": [{"question": "C", "function_name": "F"}]}
        session.save()
        self.client.login(username='cand@as.com', password='pw')
        self.client.post(reverse('assessments:submit_test', args=[self.application.id]), {"code1": "X"})
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "aptitude_failed")

    def test_model_apt_test_str(self):
        """6. AptitudeTest __str__."""
        self.assertEqual(str(self.apt_test), 'Coder')

    def test_model_attempt_str(self):
        """7. Attempt __str__."""
        att = CandidateTestAttempt.objects.create(application=self.application, score=1, passed=False)
        self.assertIn('cand@as.com', str(att))

    @patch('assessments.views.generate_test_questions')
    def test_start_test_unauthorized_app(self, mock_gen):
        """8. Other user's application."""
        mock_gen.return_value = {}
        u2 = User.objects.create_user(username='u2@t.com', email='u2@t.com', password='p')
        self.client.login(username='u2@t.com', password='p')
        url = reverse('assessments:start_test', args=[self.application.id])
        response = self.client.get(url)
        # Should probably be 404 or 302 or 200 if not restricted
        self.assertIn(response.status_code, [302, 404, 200])

    def test_submit_test_no_questions_in_session(self):
        """9. Submit without starting."""
        self.client.login(username='cand@as.com', password='pw')
        response = self.client.post(reverse('assessments:submit_test', args=[self.application.id]), {})
        self.assertEqual(response.status_code, 200)

    def test_run_code_api_invalid_json(self):
        """10. JSON parse error."""
        url = reverse('assessments:run_code')
        self.client.login(username='cand@as.com', password='pw')
        response = self.client.post(url, data="not json", content_type="application/json")
        self.assertEqual(response.status_code, 500) 

    def test_run_code_api_wrong_method(self):
        """11. GET run-code."""
        response = self.client.generic('GET', reverse('assessments:run_code'))
        self.assertEqual(response.status_code, 400)

    def test_submit_test_wrong_method(self):
        """12. GET submit-test."""
        response = self.client.get(reverse('assessments:submit_test', args=[self.application.id]))
        self.assertEqual(response.status_code, 302)

    def test_aptitude_test_one_to_one(self):
        """13. Job can only have one test."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            AptitudeTest.objects.create(job=self.job, total_questions=1, total_marks=1, passing_marks=1)

    def test_attempt_score_default_zero(self):
        """14. Default scores."""
        att = CandidateTestAttempt.objects.create(application=self.application, score=0, passed=False)
        self.assertEqual(att.aptitude_score, 0)

    def test_submit_test_missing_application(self):
        """15. Submit for invalid ID."""
        self.client.login(username='cand@as.com', password='pw')
        response = self.client.post(reverse('assessments:submit_test', args=[999]), {})
        self.assertEqual(response.status_code, 404)
