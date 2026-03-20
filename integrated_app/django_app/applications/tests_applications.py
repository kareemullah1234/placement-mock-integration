"""
Comprehensive test suite for the applications app.
Tests: Application model, apply_job, choose_test_slot, job_applicants,
       ownership checks, edge cases.
"""
import json
from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from candidates.models import CandidateProfile
from companies.models import CompanyProfile, JobPost
from applications.models import Application

User = get_user_model()


class ApplicationModelTests(TestCase):
    """Tests for the Application model."""

    def setUp(self):
        self.candidate_user = User.objects.create_user(
            username="model_cand", password="pass", role="candidate"
        )
        self.candidate = CandidateProfile.objects.create(user=self.candidate_user)
        self.company_user = User.objects.create_user(
            username="model_comp", password="pass", role="company"
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="TestCo",
            website="https://test.com", description="A test company"
        )
        self.job = JobPost.objects.create(
            company=self.company, title="Backend Dev",
            description="Build APIs", location="Remote", salary=80000
        )

    def test_create_application(self):
        """Application can be created with default status."""
        app = Application.objects.create(candidate=self.candidate, job=self.job)
        self.assertEqual(app.status, "applied")
        self.assertIsNotNone(app.applied_at)

    def test_application_str(self):
        """String representation shows username - job title."""
        app = Application.objects.create(candidate=self.candidate, job=self.job)
        self.assertEqual(str(app), "model_cand - Backend Dev")

    def test_unique_together_constraint(self):
        """Same candidate can't apply to same job twice."""
        Application.objects.create(candidate=self.candidate, job=self.job)
        with self.assertRaises(Exception):
            Application.objects.create(candidate=self.candidate, job=self.job)

    def test_status_choices(self):
        """All status choices are valid."""
        valid_statuses = [
            'applied', 'test_scheduled', 'shortlisted', 'rejected',
            'aptitude_passed', 'aptitude_failed', 'mock_passed',
            'mock_failed', 'final_selected'
        ]
        app = Application.objects.create(candidate=self.candidate, job=self.job)
        for status in valid_statuses:
            app.status = status
            app.save()
            app.refresh_from_db()
            self.assertEqual(app.status, status)

    def test_test_scheduled_at_nullable(self):
        """test_scheduled_at can be null."""
        app = Application.objects.create(candidate=self.candidate, job=self.job)
        self.assertIsNone(app.test_scheduled_at)

    def test_updated_at_changes(self):
        """updated_at changes on save."""
        app = Application.objects.create(candidate=self.candidate, job=self.job)
        old_updated = app.updated_at
        app.status = "shortlisted"
        app.save()
        app.refresh_from_db()
        self.assertGreaterEqual(app.updated_at, old_updated)

    def test_cascade_delete_candidate(self):
        """Deleting candidate deletes applications."""
        Application.objects.create(candidate=self.candidate, job=self.job)
        self.candidate_user.delete()
        self.assertEqual(Application.objects.count(), 0)

    def test_cascade_delete_job(self):
        """Deleting job deletes applications."""
        Application.objects.create(candidate=self.candidate, job=self.job)
        self.job.delete()
        self.assertEqual(Application.objects.count(), 0)


class ApplyJobViewTests(TestCase):
    """Tests for the apply_job view."""

    def setUp(self):
        self.client = Client()
        self.candidate_user = User.objects.create_user(
            username="apply_cand", password="pass", role="candidate"
        )
        self.candidate = CandidateProfile.objects.create(user=self.candidate_user)
        self.company_user = User.objects.create_user(
            username="apply_comp", password="pass", role="company"
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="ApplyCo",
            website="https://apply.com", description="Apply company"
        )
        self.job = JobPost.objects.create(
            company=self.company, title="Frontend Dev",
            description="Build UIs", location="NYC", salary=90000
        )

    def test_apply_job_creates_application(self):
        """Applying to a job creates an Application."""
        self.client.login(username="apply_cand", password="pass")
        url = reverse("applications:apply_job", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Application.objects.filter(
            candidate=self.candidate, job=self.job
        ).exists())

    def test_apply_job_redirects_to_choose_slot(self):
        """After applying, redirects to choose_test_slot."""
        self.client.login(username="apply_cand", password="pass")
        url = reverse("applications:apply_job", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("choose-slot", response.url)

    def test_apply_job_idempotent(self):
        """Applying twice doesn't create duplicate applications."""
        self.client.login(username="apply_cand", password="pass")
        url = reverse("applications:apply_job", args=[self.job.id])
        self.client.get(url)
        self.client.get(url)
        self.assertEqual(Application.objects.filter(
            candidate=self.candidate, job=self.job
        ).count(), 1)

    def test_apply_job_requires_login(self):
        """Unauthenticated user is redirected to login."""
        url = reverse("applications:apply_job", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())

    def test_apply_job_nonexistent_job(self):
        """Applying to nonexistent job returns 404."""
        self.client.login(username="apply_cand", password="pass")
        url = reverse("applications:apply_job", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_apply_job_nonexistent_candidate_profile(self):
        """User without CandidateProfile gets 404."""
        no_profile_user = User.objects.create_user(
            username="no_profile", password="pass", role="candidate"
        )
        self.client.login(username="no_profile", password="pass")
        url = reverse("applications:apply_job", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class ChooseTestSlotViewTests(TestCase):
    """Tests for the choose_test_slot view."""

    def setUp(self):
        self.client = Client()
        self.candidate_user = User.objects.create_user(
            username="slot_cand", password="pass", role="candidate"
        )
        self.candidate = CandidateProfile.objects.create(user=self.candidate_user)
        self.company_user = User.objects.create_user(
            username="slot_comp", password="pass", role="company"
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="SlotCo",
            website="https://slot.com", description="Slot company"
        )
        self.job = JobPost.objects.create(
            company=self.company, title="QA Engineer",
            description="Test things", location="SF", salary=75000
        )
        self.application = Application.objects.create(
            candidate=self.candidate, job=self.job
        )

    def test_choose_slot_page_loads(self):
        """GET choose_test_slot renders the page."""
        self.client.login(username="slot_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_choose_slot_now(self):
        """Choosing 'now' sets test_scheduled_at and redirects to test."""
        self.client.login(username="slot_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        response = self.client.post(url, {"slot": "now"})
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "test_scheduled")
        self.assertIsNotNone(self.application.test_scheduled_at)
        self.assertEqual(response.status_code, 302)
        self.assertIn("instruction", response.url.lower())

    def test_choose_slot_10min(self):
        """Choosing '10min' schedules test 10 minutes from now."""
        self.client.login(username="slot_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        before = timezone.now()
        self.client.post(url, {"slot": "10min"})
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, "test_scheduled")
        # Should be ~10 minutes from now
        expected_min = before + timedelta(minutes=9)
        expected_max = before + timedelta(minutes=11)
        self.assertTrue(expected_min <= self.application.test_scheduled_at <= expected_max)

    def test_choose_slot_1day(self):
        """Choosing '1day' schedules test 1 day from now."""
        self.client.login(username="slot_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        before = timezone.now()
        self.client.post(url, {"slot": "1day"})
        self.application.refresh_from_db()
        expected_min = before + timedelta(hours=23)
        expected_max = before + timedelta(hours=25)
        self.assertTrue(expected_min <= self.application.test_scheduled_at <= expected_max)

    def test_choose_slot_2days(self):
        """Choosing '2days' schedules test 2 days from now."""
        self.client.login(username="slot_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        before = timezone.now()
        self.client.post(url, {"slot": "2days"})
        self.application.refresh_from_db()
        expected_min = before + timedelta(hours=47)
        expected_max = before + timedelta(hours=49)
        self.assertTrue(expected_min <= self.application.test_scheduled_at <= expected_max)

    def test_choose_slot_redirects_to_dashboard_non_now(self):
        """Non-'now' slots redirect to candidate dashboard."""
        self.client.login(username="slot_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        response = self.client.post(url, {"slot": "1day"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("candidate", response.url.lower())

    def test_ownership_check_rejects_other_user(self):
        """Cannot access another user's application slot page."""
        other_user = User.objects.create_user(
            username="other_cand", password="pass", role="candidate"
        )
        CandidateProfile.objects.create(user=other_user)
        self.client.login(username="other_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirected away

    def test_requires_login(self):
        """Unauthenticated user is redirected."""
        url = reverse("applications:choose_test_slot", args=[self.application.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url.lower())

    def test_nonexistent_application(self):
        """Accessing nonexistent application returns 404."""
        self.client.login(username="slot_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class JobApplicantsViewTests(TestCase):
    """Tests for the job_applicants view (company-facing)."""

    def setUp(self):
        self.client = Client()
        self.company_user = User.objects.create_user(
            username="japp_comp", password="pass", role="company"
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="JAppCo",
            website="https://japp.com", description="JApp company"
        )
        self.job = JobPost.objects.create(
            company=self.company, title="DevOps",
            description="Infra stuff", location="LA", salary=95000
        )
        # Create some applicants
        for i in range(3):
            cand_user = User.objects.create_user(
                username=f"applicant_{i}", password="pass", role="candidate"
            )
            cand = CandidateProfile.objects.create(user=cand_user)
            Application.objects.create(candidate=cand, job=self.job)

    def test_job_applicants_page_loads(self):
        """Company can view applicants for their job."""
        self.client.login(username="japp_comp", password="pass")
        url = reverse("applications:job_applicants", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_job_applicants_shows_all_applicants(self):
        """All applicants are shown in context."""
        self.client.login(username="japp_comp", password="pass")
        url = reverse("applications:job_applicants", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(len(response.context["applications"]), 3)

    def test_other_company_cannot_view_applicants(self):
        """Another company can't see applicants for a different company's job."""
        other_comp_user = User.objects.create_user(
            username="other_comp", password="pass", role="company"
        )
        CompanyProfile.objects.create(
            user=other_comp_user, company_name="OtherCo",
            website="https://other.com", description="Other company"
        )
        self.client.login(username="other_comp", password="pass")
        url = reverse("applications:job_applicants", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)  # Redirected

    def test_candidate_cannot_view_applicants(self):
        """Candidate user without company profile is redirected."""
        cand_user = User.objects.create_user(
            username="nocomp_cand", password="pass", role="candidate"
        )
        self.client.login(username="nocomp_cand", password="pass")
        url = reverse("applications:job_applicants", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_job_returns_404(self):
        """Accessing applicants for nonexistent job returns 404."""
        self.client.login(username="japp_comp", password="pass")
        url = reverse("applications:job_applicants", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_requires_login(self):
        """Unauthenticated user is redirected."""
        url = reverse("applications:job_applicants", args=[self.job.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class ApplicationEdgeCaseTests(TestCase):
    """Edge cases and integration tests."""

    def setUp(self):
        self.client = Client()
        self.candidate_user = User.objects.create_user(
            username="edge_cand", password="pass", role="candidate"
        )
        self.candidate = CandidateProfile.objects.create(user=self.candidate_user)
        self.company_user = User.objects.create_user(
            username="edge_comp", password="pass", role="company"
        )
        self.company = CompanyProfile.objects.create(
            user=self.company_user, company_name="EdgeCo",
            website="https://edge.com", description="Edge company"
        )

    def test_apply_to_multiple_jobs(self):
        """Candidate can apply to multiple different jobs."""
        self.client.login(username="edge_cand", password="pass")
        for i in range(5):
            job = JobPost.objects.create(
                company=self.company, title=f"Job {i}",
                description=f"Desc {i}", location="Remote", salary=50000 + i * 1000
            )
            url = reverse("applications:apply_job", args=[job.id])
            self.client.get(url)
        self.assertEqual(Application.objects.filter(candidate=self.candidate).count(), 5)

    def test_multiple_candidates_same_job(self):
        """Multiple candidates can apply to the same job."""
        job = JobPost.objects.create(
            company=self.company, title="Popular Job",
            description="Everyone wants this", location="Remote", salary=120000
        )
        for i in range(5):
            cand_user = User.objects.create_user(
                username=f"multi_cand_{i}", password="pass", role="candidate"
            )
            cand = CandidateProfile.objects.create(user=cand_user)
            Application.objects.create(candidate=cand, job=job)
        self.assertEqual(Application.objects.filter(job=job).count(), 5)

    def test_invalid_slot_value(self):
        """Posting an invalid slot value handles gracefully."""
        job = JobPost.objects.create(
            company=self.company, title="Slot Test",
            description="Test", location="Remote", salary=50000
        )
        app = Application.objects.create(candidate=self.candidate, job=job)
        self.client.login(username="edge_cand", password="pass")
        url = reverse("applications:choose_test_slot", args=[app.id])
        response = self.client.post(url, {"slot": "invalid_value"})
        # Should still handle without crashing
        self.assertIn(response.status_code, [200, 302])
        app.refresh_from_db()
        # Status changes but test_scheduled_at stays None for invalid slot
        self.assertEqual(app.status, "test_scheduled")
        self.assertIsNone(app.test_scheduled_at)

    def test_full_flow_apply_and_schedule(self):
        """Complete flow: apply to job → choose slot 'now' → redirect to test."""
        job = JobPost.objects.create(
            company=self.company, title="Flow Job",
            description="Full flow", location="Remote", salary=70000
        )
        self.client.login(username="edge_cand", password="pass")
        # Step 1: Apply
        apply_url = reverse("applications:apply_job", args=[job.id])
        response = self.client.get(apply_url)
        self.assertEqual(response.status_code, 302)
        app = Application.objects.get(candidate=self.candidate, job=job)
        # Step 2: Choose slot
        slot_url = reverse("applications:choose_test_slot", args=[app.id])
        response = self.client.post(slot_url, {"slot": "now"})
        self.assertEqual(response.status_code, 302)
        app.refresh_from_db()
        self.assertEqual(app.status, "test_scheduled")
        self.assertIsNotNone(app.test_scheduled_at)
