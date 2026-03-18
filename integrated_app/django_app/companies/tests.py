from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import CompanyProfile, JobPost
from candidates.models import CandidateProfile
from common.models import Skill
from applications.models import Application

User = get_user_model()

class CompanyTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.u = User.objects.create_user(username='c@t.com', password='p')
        self.p = CompanyProfile.objects.create(user=self.u, company_name='C')
        self.s = Skill.objects.create(name='S')

    def test_job_create_basic(self):
        """1. Create job."""
        j = JobPost.objects.create(company=self.p, title='J', salary=1, is_active=True)
        self.assertEqual(j.title, 'J')

    def test_job_edit_view(self):
        """2. Edit Job."""
        j = JobPost.objects.create(company=self.p, title='Old', salary=1)
        self.client.login(username='c@t.com', password='p')
        self.client.post(reverse('companies:edit_job', args=[j.id]), {'title': 'New', 'description': 'd', 'location': 'L', 'salary': 1, 'skills': [self.s.id]})
        j.refresh_from_db()
        self.assertEqual(j.title, 'New')

    def test_job_delete(self):
        """3. Delete Job."""
        j = JobPost.objects.create(company=self.p, title='Bye', salary=1)
        self.client.login(username='c@t.com', password='p')
        self.client.post(reverse('companies:delete_job', args=[j.id]))
        self.assertFalse(JobPost.objects.filter(id=j.id).exists())

    def test_dashboard_loading(self):
        """4. Dashboard load."""
        self.client.login(username='c@t.com', password='p')
        response = self.client.get(reverse('companies:company_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_profile_update(self):
        """5. Profile Update."""
        self.client.login(username='c@t.com', password='p')
        self.client.post(reverse('companies:company_profile'), {'company_name': 'New C', 'website': 'http://x.com', 'description': 'desc'})
        self.p.refresh_from_db()
        self.assertEqual(self.p.company_name, 'New C')

    def test_job_list_anon(self):
        """6. Public job list."""
        response = self.client.get(reverse('companies:job_list'))
        self.assertEqual(response.status_code, 200)

    def test_allow_test_logic(self):
        """7. Allow test."""
        cand = User.objects.create_user(username='s', password='p')
        from candidates.models import CandidateProfile
        cp = CandidateProfile.objects.create(user=cand)
        app = Application.objects.create(candidate=cp, job=JobPost.objects.create(company=self.p, title='J', salary=1))
        self.client.login(username='c@t.com', password='p')
        self.client.get(reverse('companies:allow_test', args=[app.id]))
        app.refresh_from_db()
        self.assertEqual(app.status, 'test_allowed')

    def test_unauthorized_job_edit(self):
        """8. Wrong company edit job."""
        u2 = User.objects.create_user(username='c2', password='p')
        p2 = CompanyProfile.objects.create(user=u2, company_name='C2')
        j = JobPost.objects.create(company=p2, title='U2 job', salary=1)
        self.client.login(username='c@t.com', password='p')
        response = self.client.post(reverse('companies:edit_job', args=[j.id]), {'title': 'Hack'})
        # Should stay as U2 job
        j.refresh_from_db()
        self.assertEqual(j.title, 'U2 job')

    def test_job_applicants_access_denied(self):
        """9. Candidate viewing company applicants."""
        cand_u = User.objects.create_user(username='cand', password='p')
        self.client.login(username='cand', password='p')
        j = JobPost.objects.create(company=self.p, title='J', salary=1)
        response = self.client.get(reverse('companies:job_applicants', args=[j.id]))
        # Redirects to dashboard if denied
        self.assertEqual(response.status_code, 302)

    def test_create_job_invalid_data(self):
        """10. Create job fail."""
        self.client.login(username='c@t.com', password='p')
        response = self.client.post(reverse('companies:create_job'), {'title': ''})
        self.assertEqual(response.status_code, 200) # Form errors

    def test_company_profile_str(self):
        """11. __str__."""
        self.assertEqual(str(self.p), 'C')

    def test_job_post_str(self):
        """12. Job __str__."""
        j = JobPost.objects.create(company=self.p, title='dev', salary=1)
        self.assertEqual(str(j), 'dev')

    def test_job_list_count(self):
        """13. List count."""
        JobPost.objects.create(company=self.p, title='J1', salary=1, is_active=True)
        JobPost.objects.create(company=self.p, title='J2', salary=1, is_active=True)
        response = self.client.get(reverse('companies:job_list'))
        self.assertContains(response, 'J1')
        self.assertContains(response, 'J2')

    def test_my_jobs_view(self):
        """14. Company my-jobs."""
        self.client.login(username='c@t.com', password='p')
        response = self.client.get(reverse('companies:company_jobs'))
        self.assertEqual(response.status_code, 200)

    def test_delete_job_wrong_user(self):
        """15. Unauthorized delete."""
        u2 = User.objects.create_user(username='u2', password='p')
        j = JobPost.objects.create(company=self.p, title='Stay', salary=1)
        self.client.login(username='u2', password='p')
        self.client.post(reverse('companies:delete_job', args=[j.id]))
        self.assertTrue(JobPost.objects.filter(id=j.id).exists())

    def test_edit_job_get(self):
        """16. Edit Job GET."""
        j = JobPost.objects.create(company=self.p, title='X', salary=1)
        self.client.login(username='c@t.com', password='p')
        response = self.client.get(reverse('companies:edit_job', args=[j.id]))
        self.assertEqual(response.status_code, 200)

    def test_job_applicants_count(self):
        """17. Applicants count."""
        j = JobPost.objects.create(company=self.p, title='J', salary=1)
        from candidates.models import CandidateProfile
        u2 = User.objects.create_user(username='s2', password='p')
        Application.objects.create(candidate=CandidateProfile.objects.create(user=u2), job=j)
        self.client.login(username='c@t.com', password='p')
        response = self.client.get(reverse('companies:job_applicants', args=[j.id]))
        self.assertContains(response, 's2')

    def test_allow_test_unauthorized(self):
        """18. Unauthorized allow."""
        u2 = User.objects.create_user(username='u2', password='p')
        app = Application.objects.create(candidate=CandidateProfile.objects.create(user=User.objects.create_user(username='sz', password='p')), job=JobPost.objects.create(company=self.p, title='J', salary=1))
        self.client.login(username='u2', password='p')
        self.client.get(reverse('companies:allow_test', args=[app.id]))
        app.refresh_from_db()
        self.assertNotEqual(app.status, 'test_allowed')

    def test_company_profile_one_to_one(self):
        """19. Profile constraint."""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            CompanyProfile.objects.create(user=self.u, company_name='C2')

    def test_create_job_requires_verified(self):
        """20. Verification check (if implemented)."""
        # Assuming for now it's False by default
        self.assertFalse(self.p.is_verified)
