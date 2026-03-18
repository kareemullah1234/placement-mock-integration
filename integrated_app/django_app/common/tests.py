from django.test import TestCase, Client
from django.urls import reverse
from .models import Skill
from django.contrib.auth import get_user_model
from candidates.models import CandidateProfile
from companies.models import CompanyProfile, JobPost

User = get_user_model()

class CommonTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_skill_creation(self):
        """1. Basic skill."""
        s = Skill.objects.create(name='C++')
        self.assertEqual(str(s), 'C++')

    def test_skill_uniqueness(self):
        """2. Unique names."""
        Skill.objects.create(name='SQL')
        with self.assertRaises(Exception):
            Skill.objects.create(name='SQL')

    def test_admin_stats_api_authenticated(self):
        """3. Stats API."""
        User.objects.create_user(username='cand1@gmail.com', password='p')
        # Stats view usually accessible
        response = self.client.get(reverse('admin_stats'))
        self.assertEqual(response.status_code, 200)

    def test_admin_users_api(self):
        """4. Admin Users list."""
        User.objects.create_user(username='user1', password='p')
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json()['users'], list)

    def test_stats_data_accuracy(self):
        """5. Stats content."""
        u1 = User.objects.create_user(username='c1@gmail.com', password='p')
        CandidateProfile.objects.create(user=u1)
        u2 = User.objects.create_user(username='h1@big.co', password='p')
        CompanyProfile.objects.create(user=u2, company_name='BigCo')
        JobPost.objects.create(company=CompanyProfile.objects.first(), title='J', salary=1, is_active=True)
        
        response = self.client.get(reverse('admin_stats'))
        data = response.json()
        self.assertEqual(data['candidates'], 1)
        self.assertEqual(data['companies'], 1)
        self.assertEqual(data['jobs'], 1)

    def test_skill_str(self):
        """6. __str__."""
        s = Skill.objects.create(name='React')
        self.assertEqual(str(s), 'React')

    def test_admin_users_content(self):
        """7. Users list content."""
        u = User.objects.create_user(username='test_user', email='test@t.com', password='p')
        CandidateProfile.objects.create(user=u)
        response = self.client.get(reverse('admin_users'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        found = any(user['name'] == 'test_user' for user in data['users'])
        self.assertTrue(found)

    def test_stats_api_zero_counts(self):
        """8. Empty stats."""
        # Ensure db is fresh (TestCase does this)
        response = self.client.get(reverse('admin_stats'))
        data = response.json()
        self.assertEqual(data['candidates'], 0)

    def test_skill_name_max_length(self):
        """9. Name length."""
        name = "A" * 100
        s = Skill.objects.create(name=name)
        self.assertEqual(len(s.name), 100)

    def test_url_reversing(self):
        """10. URL names."""
        self.assertEqual(reverse('admin_stats'), '/common/admin/stats/')
