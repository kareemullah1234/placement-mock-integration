import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse

from candidates.models import CandidateProfile
from companies.models import CompanyProfile

User = get_user_model()

def register(request):
    """View for manual registration via HTML form."""
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not username:
            messages.error(request, "Username is required.")
            return render(request, "accounts/register.html")

        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            messages.error(request, "Username or Email already exists.")
            return render(request, "accounts/register.html")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        domain = email.split("@")[1]
        # Auto detect role based on domain
        if domain in ["gmail.com", "yahoo.com", "outlook.com"]:
            user.role = 'candidate'
            user.save()
            CandidateProfile.objects.create(user=user)
        else:
            user.role = 'company'
            user.save()
            CompanyProfile.objects.create(user=user)

        messages.success(request, "Registration successful! Please login.")
        return redirect("login")

    return render(request, "accounts/register.html")

class CustomLoginView(LoginView):
    """Extends Django's LoginView with role-based routing."""
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user
        if user.role == 'candidate':
            return reverse('candidate_dashboard')
        elif user.role == 'company':
            return reverse('companies:company_dashboard')
        else:
            return '/admin/'

def user_login(request):
    """Alternative manual login view (if not using CustomLoginView)."""
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if user.role == 'admin' or user.is_superuser:
                return redirect("admin_dashboard")
            elif user.role == 'candidate':
                candidate, _ = CandidateProfile.objects.get_or_create(user=user)
                if not candidate.resume:
                    messages.info(request, "Please upload your resume to get started.")
                    return redirect("candidates:candidate_profile")
                return redirect("candidates:candidate_dashboard")
            elif user.role == 'company':
                company, _ = CompanyProfile.objects.get_or_create(user=user)
                if not company.company_name:
                    return redirect("companies:company_profile")
                return redirect("companies:company_dashboard")
        else:
            return render(request, "accounts/login.html", {"error": "Invalid username or password"})

    return render(request, "accounts/login.html")

def redirect_user(request):
    """Central gateway for authenticated users to land on their dashboard."""
    if not request.user.is_authenticated:
        return redirect("login")
        
    if request.user.is_superuser or request.user.role == 'admin':
        return redirect("admin_dashboard")

    if request.user.role == 'candidate':
        candidate, created = CandidateProfile.objects.get_or_create(user=request.user)
        # Force resume upload if missing
        if not candidate.resume:
            messages.info(request, "Welcome! Please upload your resume to complete your profile before accessing the dashboard.")
            return redirect("candidates:candidate_profile")
        return redirect("candidates:candidate_dashboard")

    if request.user.role == 'company':
        return redirect("companies:company_dashboard")

    return redirect("login")

@csrf_exempt
def register_api(request):
    """REST API for user registration."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name", "")
            email = data.get("email")
            password = data.get("password")

            if not email or not password:
                return JsonResponse({"error": "Missing email or password"}, status=400)

            if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
                return JsonResponse({"error": "User with this email/username already exists"}, status=400)

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name
            )
            # Default to candidate for API sessions (usually React/App)
            user.role = 'candidate'
            user.save()
            CandidateProfile.objects.create(user=user)

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"message": "Register API working"})

@csrf_exempt
def login_api(request):
    """REST API for user login."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                return JsonResponse({"success": True, "user_id": user.id})

            return JsonResponse({"error": "Invalid login"}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"message": "Login API working"}, status=400)

def dashboard(request):
    """Simple status check view."""
    return HttpResponse("Welcome to Dashboard 🚀")