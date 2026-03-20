"""
Comprehensive test suite for the accounts app.
Tests: User model, registration (form + API), login (form + API),
       role detection, redirects, logout, edge cases.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from candidates.models import CandidateProfile
from companies.models import CompanyProfile

User = get_user_model()


class UserModelTests(TestCase):
    """Tests for the custom User model."""

    def test_create_user_with_role(self):
        """User can be created with a role field."""
        user = User.objects.create_user(
            username="testuser", password="testpass123", role="candidate"
        )
        self.assertEqual(user.role, "candidate")
        self.assertTrue(user.check_password("testpass123"))

    def test_create_company_user(self):
        """User can be created with company role."""
        user = User.objects.create_user(
            username="companyuser", password="pass123", role="company"
        )
        self.assertEqual(user.role, "company")

    def test_create_admin_user(self):
        """User can be created with admin role."""
        user = User.objects.create_user(
            username="adminuser", password="pass123", role="admin"
        )
        self.assertEqual(user.role, "admin")

    def test_create_superuser(self):
        """Superuser creation works correctly."""
        user = User.objects.create_superuser(
            username="superadmin", password="superpass123", email="admin@test.com"
        )
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_user_string_representation(self):
        """User __str__ returns the username."""
        user = User.objects.create_user(username="struser", password="pass123")
        self.assertEqual(str(user), "struser")


class RegistrationPageTests(TestCase):
    """Tests for the HTML registration form."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")

    def test_register_page_loads(self):
        """GET /accounts/register/ returns 200."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)

    def test_register_candidate_gmail(self):
        """Registration with @gmail.com creates a candidate."""
        response = self.client.post(self.register_url, {
            "username": "john_gmail",
            "email": "john@gmail.com",
            "password": "securepass123",
        })
        user = User.objects.get(username="john_gmail")
        self.assertEqual(user.role, "candidate")
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())
        # Should redirect to login after successful registration
        self.assertEqual(response.status_code, 302)

    def test_register_candidate_yahoo(self):
        """Registration with @yahoo.com creates a candidate."""
        self.client.post(self.register_url, {
            "username": "jane_yahoo",
            "email": "jane@yahoo.com",
            "password": "securepass123",
        })
        user = User.objects.get(username="jane_yahoo")
        self.assertEqual(user.role, "candidate")
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())

    def test_register_candidate_outlook(self):
        """Registration with @outlook.com creates a candidate."""
        self.client.post(self.register_url, {
            "username": "bob_outlook",
            "email": "bob@outlook.com",
            "password": "securepass123",
        })
        user = User.objects.get(username="bob_outlook")
        self.assertEqual(user.role, "candidate")
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())

    def test_register_company_custom_domain(self):
        """Registration with non-gmail/yahoo/outlook creates a company."""
        self.client.post(self.register_url, {
            "username": "acme_user",
            "email": "hiring@acme.com",
            "password": "securepass123",
        })
        user = User.objects.get(username="acme_user")
        self.assertEqual(user.role, "company")
        self.assertTrue(CompanyProfile.objects.filter(user=user).exists())

    def test_register_company_microsoft_domain(self):
        """Registration with @microsoft.com creates a company."""
        self.client.post(self.register_url, {
            "username": "ms_user",
            "email": "dev@microsoft.com",
            "password": "securepass123",
        })
        user = User.objects.get(username="ms_user")
        self.assertEqual(user.role, "company")
        self.assertTrue(CompanyProfile.objects.filter(user=user).exists())

    def test_register_duplicate_username(self):
        """Duplicate username shows error, does not create new user."""
        User.objects.create_user(username="duplicate", email="dup1@gmail.com", password="pass")
        response = self.client.post(self.register_url, {
            "username": "duplicate",
            "email": "dup2@gmail.com",
            "password": "pass",
        })
        self.assertEqual(User.objects.filter(username="duplicate").count(), 1)
        # Should re-render the registration page (200), not redirect
        self.assertEqual(response.status_code, 200)

    def test_register_duplicate_email(self):
        """Duplicate email shows error."""
        User.objects.create_user(username="user1", email="same@gmail.com", password="pass")
        response = self.client.post(self.register_url, {
            "username": "user2",
            "email": "same@gmail.com",
            "password": "pass",
        })
        self.assertEqual(User.objects.filter(email="same@gmail.com").count(), 1)
        self.assertEqual(response.status_code, 200)

    def test_register_empty_username(self):
        """Registration with empty username returns the form again."""
        response = self.client.post(self.register_url, {
            "username": "",
            "email": "empty@gmail.com",
            "password": "pass",
        })
        self.assertFalse(User.objects.filter(email="empty@gmail.com").exists())
        self.assertEqual(response.status_code, 200)


class LoginPageTests(TestCase):
    """Tests for the HTML login form."""

    def setUp(self):
        self.client = Client()
        self.login_url = reverse("login")
        # Create a candidate user
        self.candidate_user = User.objects.create_user(
            username="cand_login", password="cand_pass", role="candidate"
        )
        CandidateProfile.objects.create(user=self.candidate_user)
        # Create a company user
        self.company_user = User.objects.create_user(
            username="comp_login", password="comp_pass", role="company"
        )
        CompanyProfile.objects.create(user=self.company_user)

    def test_login_page_loads(self):
        """GET /accounts/login/ returns 200."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

    def test_candidate_login_redirects_to_dashboard(self):
        """Candidate login redirects to candidate dashboard."""
        response = self.client.post(self.login_url, {
            "username": "cand_login",
            "password": "cand_pass",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("candidate", response.url.lower())

    def test_company_login_redirects_to_company_dashboard(self):
        """Company login redirects to company area."""
        response = self.client.post(self.login_url, {
            "username": "comp_login",
            "password": "comp_pass",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("compan", response.url.lower())

    def test_invalid_credentials(self):
        """Invalid credentials stay on the login page."""
        response = self.client.post(self.login_url, {
            "username": "cand_login",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, 200)  # Re-renders the page

    def test_nonexistent_user(self):
        """Login with nonexistent username stays on login page."""
        response = self.client.post(self.login_url, {
            "username": "ghost_user",
            "password": "nopass",
        })
        self.assertEqual(response.status_code, 200)

    def test_empty_credentials(self):
        """Empty username and password stays on login page."""
        response = self.client.post(self.login_url, {
            "username": "",
            "password": "",
        })
        self.assertEqual(response.status_code, 200)


class LogoutTests(TestCase):
    """Tests for logout functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="logout_user", password="pass123", role="candidate"
        )
        CandidateProfile.objects.create(user=self.user)

    def test_logout_redirects_to_login(self):
        """After logout, user is redirected to login page."""
        self.client.login(username="logout_user", password="pass123")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_logout_clears_session(self):
        """After logout, accessing protected pages redirects to login."""
        self.client.login(username="logout_user", password="pass123")
        self.client.post(reverse("logout"))
        # After logout, accessing dashboard should redirect to login
        response = self.client.get(reverse("candidate_dashboard"))
        self.assertEqual(response.status_code, 302)


class RedirectViewTests(TestCase):
    """Tests for the redirect_user view."""

    def setUp(self):
        self.client = Client()
        self.redirect_url = reverse("role_redirect")

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated user is redirected to login."""
        response = self.client.get(self.redirect_url)
        self.assertEqual(response.status_code, 302)

    def test_candidate_redirects_to_candidate_dashboard(self):
        """Authenticated candidate goes to candidate dashboard."""
        user = User.objects.create_user(
            username="redir_cand", password="pass", role="candidate"
        )
        CandidateProfile.objects.create(user=user)
        self.client.login(username="redir_cand", password="pass")
        response = self.client.get(self.redirect_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("candidate", response.url.lower())

    def test_company_redirects_to_company_dashboard(self):
        """Authenticated company user goes to company dashboard."""
        user = User.objects.create_user(
            username="redir_comp", password="pass", role="company"
        )
        CompanyProfile.objects.create(user=user)
        self.client.login(username="redir_comp", password="pass")
        response = self.client.get(self.redirect_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("compan", response.url.lower())

    def test_superuser_redirects_to_admin(self):
        """Superuser is redirected to admin panel."""
        User.objects.create_superuser(
            username="redir_super", password="pass", email="s@t.com"
        )
        self.client.login(username="redir_super", password="pass")
        response = self.client.get(self.redirect_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("admin", response.url)


class RegisterAPITests(TestCase):
    """Tests for the REST API registration endpoint."""

    def setUp(self):
        self.client = Client()
        self.api_url = "/accounts/api/register/"

    def test_api_register_success(self):
        """API registration with valid data returns success."""
        payload = {"email": "api_user@gmail.com", "password": "securepass", "name": "API User"}
        response = self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        # API always creates candidate role
        user = User.objects.get(email="api_user@gmail.com")
        self.assertEqual(user.role, "candidate")
        self.assertTrue(CandidateProfile.objects.filter(user=user).exists())

    def test_api_register_missing_email(self):
        """API registration without email returns 400."""
        payload = {"password": "pass123"}
        response = self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_api_register_missing_password(self):
        """API registration without password returns 400."""
        payload = {"email": "nopass@gmail.com"}
        response = self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_api_register_duplicate(self):
        """API registration with existing email returns 400."""
        User.objects.create_user(
            username="existing@test.com", email="existing@test.com", password="pass"
        )
        payload = {"email": "existing@test.com", "password": "pass123"}
        response = self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_api_register_get_method(self):
        """GET request to register API returns info message."""
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)

    def test_api_register_sets_first_name(self):
        """API registration stores the name as first_name."""
        payload = {"email": "named@gmail.com", "password": "pass", "name": "John Doe"}
        self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        user = User.objects.get(email="named@gmail.com")
        self.assertEqual(user.first_name, "John Doe")


class LoginAPITests(TestCase):
    """Tests for the REST API login endpoint."""

    def setUp(self):
        self.client = Client()
        self.api_url = "/accounts/api/login/"
        self.user = User.objects.create_user(
            username="api_login_user", password="api_pass123", role="candidate"
        )

    def test_api_login_success(self):
        """API login with valid credentials returns success + user_id."""
        payload = {"username": "api_login_user", "password": "api_pass123"}
        response = self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("user_id"), self.user.id)

    def test_api_login_invalid_credentials(self):
        """API login with wrong password returns 401."""
        payload = {"username": "api_login_user", "password": "wrongpass"}
        response = self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_login_nonexistent_user(self):
        """API login with nonexistent user returns 401."""
        payload = {"username": "ghost", "password": "nopass"}
        response = self.client.post(
            self.api_url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_api_login_get_method(self):
        """GET request to login API returns 400."""
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 400)


class DashboardViewTests(TestCase):
    """Tests for the simple dashboard status view."""

    def test_dashboard_returns_200(self):
        """GET /accounts/dashboard/ returns 200."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dashboard", response.content)


class EdgeCaseTests(TestCase):
    """Edge cases and worst-case scenario tests."""

    def setUp(self):
        self.client = Client()
        self.register_url = reverse("register")
        self.login_url = reverse("login")

    def test_sql_injection_in_username(self):
        """SQL injection attempt in username is harmless."""
        response = self.client.post(self.register_url, {
            "username": "'; DROP TABLE accounts_user; --",
            "email": "sqli@gmail.com",
            "password": "pass123",
        })
        # Should either succeed or fail gracefully, no 500 error
        self.assertIn(response.status_code, [200, 302])

    def test_xss_in_username(self):
        """XSS attempt in username is handled safely."""
        response = self.client.post(self.register_url, {
            "username": "<script>alert('xss')</script>",
            "email": "xss@gmail.com",
            "password": "pass123",
        })
        self.assertIn(response.status_code, [200, 302])

    def test_very_long_username(self):
        """Very long username doesn't crash the server."""
        long_name = "a" * 500
        response = self.client.post(self.register_url, {
            "username": long_name,
            "email": "long@gmail.com",
            "password": "pass123",
        })
        # Should handle gracefully (200 = error shown, 302 = redirect, 500 = fail)
        self.assertNotEqual(response.status_code, 500)

    def test_special_chars_password(self):
        """Password with special chars works for registration + login."""
        self.client.post(self.register_url, {
            "username": "special_pwd_user",
            "email": "special@gmail.com",
            "password": "P@$$w0rd!#%&*()+=",
        })
        user = User.objects.get(username="special_pwd_user")
        self.assertTrue(user.check_password("P@$$w0rd!#%&*()+="))

    def test_concurrent_api_registrations(self):
        """Multiple API registrations with different emails succeed."""
        api_url = "/accounts/api/register/"
        for i in range(5):
            payload = {"email": f"bulk_{i}@test.com", "password": "pass123", "name": f"User {i}"}
            response = self.client.post(
                api_url,
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username__startswith="bulk_").count(), 5)

    def test_login_after_registration(self):
        """Full flow: register via form, then login."""
        # Register
        self.client.post(self.register_url, {
            "username": "flow_user",
            "email": "flow@gmail.com",
            "password": "flowpass123",
        })
        # Login
        response = self.client.post(self.login_url, {
            "username": "flow_user",
            "password": "flowpass123",
        })
        self.assertEqual(response.status_code, 302)

    def test_api_register_then_api_login(self):
        """Full flow: register via API, then login via API."""
        reg_url = "/accounts/api/register/"
        login_url = "/accounts/api/login/"
        # Register
        payload = {"email": "apiflow@test.com", "password": "apipass123", "name": "API Flow"}
        self.client.post(reg_url, data=json.dumps(payload), content_type="application/json")
        # Login (API uses username, which is set to email)
        login_payload = {"username": "apiflow@test.com", "password": "apipass123"}
        response = self.client.post(
            login_url,
            data=json.dumps(login_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get("success"))

    def test_empty_json_body_api_register(self):
        """Empty JSON body to API register returns 400."""
        response = self.client.post(
            "/accounts/api/register/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_json_body_api_login(self):
        """Malformed JSON body returns 500 error (graceful failure)."""
        response = self.client.post(
            "/accounts/api/login/",
            data="this is not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 500)
