from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from candidates.models import CandidateProfile
from companies.models import CompanyProfile

User = get_user_model()


def register(request):

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        domain = email.split("@")[1]

        # Auto detect role
        if domain in ["gmail.com", "yahoo.com", "outlook.com"]:
            CandidateProfile.objects.create(user=user)
        else:
            CompanyProfile.objects.create(user=user)

        return redirect("login")

    return render(request, "accounts/register.html")

from django.contrib.auth.views import LoginView

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_success_url(self):
        user = self.request.user

        if user.role == 'candidate':
            return '/candidate/dashboard/'
        elif user.role == 'company':
            return '/company/dashboard/'
        else:
            return '/admin/'
        
from django.http import HttpResponse

def dashboard(request):
    return HttpResponse("Welcome to Dashboard 🚀")

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login

def user_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if CandidateProfile.objects.filter(user=user).exists():
                return redirect("job_list")
            elif CompanyProfile.objects.filter(user=user).exists():
                return redirect("company_dashboard")

    return render(request, "accounts/login.html")

from candidates.models import CandidateProfile
from companies.models import CompanyProfile
from django.shortcuts import redirect

def redirect_user(request):

    if request.user.is_superuser:
        return redirect("/admin/")

    if CandidateProfile.objects.filter(user=request.user).exists():
        return redirect("candidate_dashboard")

    if CompanyProfile.objects.filter(user=request.user).exists():
        return redirect("company_dashboard")

    return redirect("login")