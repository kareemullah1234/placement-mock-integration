from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from candidates.models import CandidateProfile
from companies.models import CompanyProfile, JobPost
from .models import Application

User = get_user_model()

class ApplicationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.comp_user = User.objects.create_user(username='c@t.com', password='p')
        self.comp_prof = CompanyProfile.objects.create(user=self.comp_user, company_name='C')
        self.job = JobPost.objects.create(company=self.comp_prof, title='J', salary=10, is_active=True)
        self.cand_user = User.objects.create_user(username='s@t.com', password='p')
        self.cand_prof = CandidateProfile.objects.create(user=self.cand_user)

    def test_apply_job_flow(self):
        """1. Basic Apply."""
        self.client.login(username='s@t.com', password='p')
        response = self.client.get(reverse('apply_job', args=[self.job.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Application.objects.filter(candidate=self.cand_prof, job=self.job).exists())

    def test_slot_selection_now(self):
        """2. Slot Now."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job)
        self.client.login(username='s@t.com', password='p')
        response = self.client.post(reverse('choose_test_slot', args=[app.id]), {'slot': 'now'})
        app.refresh_from_db()
        self.assertEqual(app.status, 'test_scheduled')

    def test_slot_selection_10min(self):
        """3. Slot 10min."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job)
        self.client.login(username='s@t.com', password='p')
        self.client.post(reverse('choose_test_slot', args=[app.id]), {'slot': '10min'})
        app.refresh_from_db()
        self.assertAlmostEqual(app.test_scheduled_at, timezone.now() + timedelta(minutes=10), delta=timedelta(seconds=5))

    def test_slot_selection_1day(self):
        """4. Slot 1day."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job)
        self.client.login(username='s@t.com', password='p')
        self.client.post(reverse('choose_test_slot', args=[app.id]), {'slot': '1day'})
        app.refresh_from_db()
        self.assertAlmostEqual(app.test_scheduled_at, timezone.now() + timedelta(days=1), delta=timedelta(seconds=5))

    def test_job_applicants_view(self):
        """5. Applicant list for company."""
        Application.objects.create(candidate=self.cand_prof, job=self.job)
        self.client.login(username='c@t.com', password='p')
        response = self.client.get(reverse('job_applicants', args=[self.job.id]))
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_apply(self):
        """6. Anon apply."""
        response = self.client.get(reverse('apply_job', args=[self.job.id]))
        self.assertEqual(response.status_code, 302)

    def test_duplicate_application_prevention(self):
        """7. Unique constraint test."""
        Application.objects.create(candidate=self.cand_prof, job=self.job)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Application.objects.create(candidate=self.cand_prof, job=self.job)

    def test_apply_nonexistent_job(self):
        """8. Apply to invalid ID."""
        self.client.login(username='s@t.com', password='p')
        response = self.client.get(reverse('apply_job', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_choose_slot_wrong_user(self):
        """9. Other user trying to choose slot."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job)
        other_user = User.objects.create_user(username='o@t.com', password='p')
        self.client.login(username='o@t.com', password='p')
        response = self.client.post(reverse('choose_test_slot', args=[app.id]), {'slot': 'now'})
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)

    def test_model_str(self):
        """10. __str__ test."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job)
        self.assertEqual(str(app), f"{self.cand_user.username} - {self.job.title}")

    def test_status_choices(self):
        """11. Verify status codes."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job, status='mock_passed')
        self.assertEqual(app.status, 'mock_passed')

    def test_applied_at_auto_added(self):
        """12. Timestamp test."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job)
        self.assertIsNotNone(app.applied_at)

    def test_job_applicants_empty(self):
        """13. No applicants view."""
        self.client.login(username='c@t.com', password='p')
        response = self.client.get(reverse('job_applicants', args=[self.job.id]))
        self.assertEqual(response.status_code, 200)

    def test_choose_slot_invalid_id(self):
        """14. Choose slot on non-existent app."""
        self.client.login(username='s@t.com', password='p')
        response = self.client.post(reverse('choose_test_slot', args=[999]), {'slot': 'now'})
        self.assertEqual(response.status_code, 404)

    def test_slot_selection_2days(self):
        """15. Slot 2days."""
        app = Application.objects.create(candidate=self.cand_prof, job=self.job)
        self.client.login(username='s@t.com', password='p')
        self.client.post(reverse('choose_test_slot', args=[app.id]), {'slot': '2days'})
        app.refresh_from_db()
        self.assertAlmostEqual(app.test_scheduled_at, timezone.now() + timedelta(days=2), delta=timedelta(seconds=5))
