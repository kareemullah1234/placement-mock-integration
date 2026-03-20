import os

def update_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated: {path}")

# --- ACCOUNTS ---
update_file("accounts/templates/accounts/register.html", """{% extends 'base.html' %}
{% block title %}Register | PlacementAI{% endblock %}
{% block content %}
<div class="flex items-center justify-center min-h-[70vh] w-full">
    <div class="w-full max-w-md glass-card rounded-[2rem] p-8 sm:p-10 relative z-10">
        <div class="text-center mb-10">
            <div class="text-4xl mb-6">
                <i class="fas fa-sparkles gemini-gradient-text"></i>
            </div>
            <h1 class="text-3xl font-bold text-[#ffffff] tracking-tight mb-2">Create Account</h1>
            <p class="text-[#c4c7c5] text-sm">Join the next generation of recruiting</p>
        </div>

        <form method="post" class="space-y-6">
            {% csrf_token %}
            <div>
                <label class="block text-xs font-semibold text-[#8e918f] uppercase tracking-widest mb-2 ml-1">Username</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-user-circle text-[#8e918f] group-focus-within:text-[#a8c7fa] transition-colors"></i>
                    </div>
                    <input type="text" name="username" required class="form-input pl-11" placeholder="Choose a username">
                </div>
            </div>

            <div>
                <label class="block text-xs font-semibold text-[#8e918f] uppercase tracking-widest mb-2 ml-1">Email Address</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-envelope text-[#8e918f] group-focus-within:text-[#a8c7fa] transition-colors"></i>
                    </div>
                    <input type="email" name="email" required class="form-input pl-11 focus:!border-[#a8c7fa]" placeholder="name@domain.com">
                </div>
                <p class="mt-2 text-[10px] text-[#8e918f] font-medium tracking-wide">* Candidate: Gmail/Yahoo | Company: Corporate Email</p>
            </div>

            <div>
                <label class="block text-xs font-semibold text-[#8e918f] uppercase tracking-widest mb-2 ml-1">Password</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-lock text-[#8e918f] group-focus-within:text-[#a8c7fa] transition-colors"></i>
                    </div>
                    <input type="password" name="password" required class="form-input pl-11" placeholder="••••••••">
                </div>
            </div>

            <button type="submit" class="w-full gemini-gradient-bg text-white font-bold py-4 rounded-2xl shadow-lg transform hover:-translate-y-0.5 transition-all duration-200 uppercase tracking-widest text-sm mt-4">
                Get Started
            </button>
        </form>

        <div class="mt-10 pt-8 border-t border-[#444746] text-center">
            <p class="text-[#c4c7c5] text-sm">
                Already have an account? 
                <a href="{% url 'login' %}" class="gemini-gradient-text font-bold ml-1">Sign In</a>
            </p>
        </div>
    </div>
</div>
{% endblock %}""")

# --- CANDIDATES ---
update_file("candidates/templates/candidates/dashboard.html", """{% extends 'base.html' %}
{% load tz %}
{% block title %}Dashboard | PlacementAI{% endblock %}
{% block content %}
<div class="mb-12">
    <h1 class="text-4xl font-bold text-[#ffffff] mb-2">Welcome back, <span class="gemini-gradient-text">{{ request.user.username }}</span></h1>
    <p class="text-[#c4c7c5]">Track your applications and upcoming assessments.</p>
</div>

<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
    <div class="glass-card rounded-[2rem] p-8 hover:-translate-y-1 transition-transform">
        <div class="w-12 h-12 bg-[#004a77]/30 rounded-2xl flex items-center justify-center text-[#a8c7fa] mb-6">
            <i class="fas fa-paper-plane text-xl"></i>
        </div>
        <h3 class="text-[#8e918f] text-xs font-bold uppercase tracking-widest mb-1">Applied</h3>
        <p class="text-4xl font-bold text-[#ffffff]">{{ applications|length }}</p>
    </div>
    
    <div class="glass-card rounded-[2rem] p-8 hover:-translate-y-1 transition-transform">
        <div class="w-12 h-12 bg-[#004a77]/30 rounded-2xl flex items-center justify-center text-[#d3e3fd] mb-6">
            <i class="fas fa-check-double text-xl"></i>
        </div>
        <h3 class="text-[#8e918f] text-xs font-bold uppercase tracking-widest mb-1">Cleared</h3>
        <p class="text-4xl font-bold text-[#ffffff]">0</p>
    </div>

    <div class="glass-card rounded-[2rem] p-8 hover:-translate-y-1 transition-transform">
        <div class="w-12 h-12 bg-[#004a77]/30 rounded-2xl flex items-center justify-center text-[#a8c7fa] mb-6">
            <i class="fas fa-calendar-check text-xl"></i>
        </div>
        <h3 class="text-[#8e918f] text-xs font-bold uppercase tracking-widest mb-1">Upcoming</h3>
        <p class="text-4xl font-bold text-[#ffffff]">0</p>
    </div>
</div>

<h2 class="text-2xl font-bold text-[#ffffff] mb-6">Your Applications</h2>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    {% for app in applications %}
    <div class="glass-card rounded-[2rem] p-8 group">
        <div class="flex justify-between items-start mb-6">
            <div>
                <h3 class="text-xl font-bold text-[#ffffff] group-hover:text-[#a8c7fa] transition-colors">{{ app.job.title }}</h3>
                <p class="text-[#c4c7c5] text-sm mt-1 flex items-center">
                    <i class="fas fa-building mr-2 text-[#8e918f]"></i> {{ app.job.company.company_name }}
                </p>
            </div>
            <span class="px-4 py-1.5 bg-[#282a2c] rounded-full font-bold text-[10px] border border-[#444746] tracking-widest uppercase
                {% if app.status == 'applied' %}text-yellow-400
                {% elif app.status == 'shortlisted' %}text-[#a8c7fa]
                {% elif app.status == 'test_scheduled' %}text-[#d3e3fd]
                {% elif app.status == 'aptitude_passed' %}text-green-400
                {% elif app.status == 'interview_scheduled' %}text-orange-400
                {% else %}text-[#c4c7c5]{% endif %}">
                {{ app.status|title }}
            </span>
        </div>
        
        <div class="flex gap-4 mt-8">
            {% if app.status == 'applied' %}
                <a href="{% url 'upload_resume' app.job.id %}" class="flex-1 text-center py-3 bg-[#282a2c] hover:bg-[#444746] text-[#e3e3e3] border border-[#444746] rounded-xl text-xs font-bold uppercase tracking-widest transition-all">
                    Upload Resume
                </a>
            {% elif app.status == 'test_scheduled' %}
                <a href="{% url 'assessments:start_test' app.id %}" class="flex-1 text-center py-3 gemini-gradient-bg text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all">
                    Start Assessment
                </a>
            {% elif app.status == 'aptitude_passed' %}
                <a href="{% url 'applications:choose_test_slot' app.id %}" class="flex-1 text-center py-3 gemini-gradient-bg text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all">
                    Schedule Interview
                </a>
            {% elif app.status == 'interview_scheduled' %}
                <a href="{% url 'interviews:candidate_dashboard' %}" class="flex-1 text-center py-3 gemini-gradient-bg text-white rounded-xl text-xs font-bold uppercase tracking-widest transition-all">
                    Go to Interview
                </a>
            {% else %}
                <div class="flex-1 text-center py-3 bg-[#1e1f20] text-[#8e918f] border border-[#444746] rounded-xl text-xs font-bold uppercase tracking-widest opacity-60">
                    Application Pending
                </div>
            {% endif %}
        </div>
    </div>
    {% empty %}
    <div class="col-span-full glass-card rounded-[2.5rem] p-20 text-center border-dashed border-2 border-[#444746]">
        <div class="text-5xl mb-6">
            <i class="fas fa-search text-[#8e918f]"></i>
        </div>
        <h3 class="text-2xl font-bold text-[#ffffff] mb-2">No applications yet</h3>
        <p class="text-[#8e918f] mb-8">Start your journey by exploring available roles.</p>
        <a href="{% url 'companies:job_list' %}" class="inline-block px-10 py-4 gemini-gradient-bg text-white rounded-2xl font-bold uppercase tracking-widest text-xs shadow-lg">Browse Companies</a>
    </div>
    {% endfor %}
</div>
{% endblock %}""")

update_file("candidates/templates/candidates/profile.html", """{% extends 'base.html' %}
{% block title %}My Profile | PlacementAI{% endblock %}
{% block content %}
<div class="max-w-3xl mx-auto w-full">
    <div class="glass-card rounded-[2.5rem] p-10 sm:p-12">
        <div class="flex items-center gap-6 mb-12 border-b border-[#444746] pb-10">
            <div class="w-20 h-20 bg-[#282a2c] rounded-3xl flex items-center justify-center border border-[#444746] text-3xl">
                <i class="fas fa-pen-sparkle gemini-gradient-text"></i>
            </div>
            <div>
                <h1 class="text-3xl font-bold text-[#ffffff]">Candidate Profile</h1>
                <p class="text-[#c4c7c5]">Update your information for better matching</p>
            </div>
        </div>

        <form method="POST" enctype="multipart/form-data" class="space-y-8">
            {% csrf_token %}
            <div>
                <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Contact Number</label>
                <input type="text" name="phone" value="{{ candidate.phone }}" class="form-input" placeholder="+1 (234) 567-8900">
            </div>

            <div class="bg-[#1e1f20] rounded-2xl p-8 border border-[#444746] relative overflow-hidden group">
                <div class="relative z-10">
                    <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-4">Resume Upload</label>
                    <input type="file" name="resume" class="block w-full text-sm text-[#c4c7c5] file:mr-4 file:py-2.5 file:px-6 file:rounded-full file:border-0 file:text-xs file:font-black file:bg-[#444746] file:text-[#ffffff] hover:file:bg-[#5f6368] cursor-pointer">
                    <p class="mt-4 text-xs text-[#8e918f]">Accepted formats: PDF, DOCX (Max 5MB)</p>
                </div>
                {% if candidate.resume %}
                <div class="mt-6 flex items-center gap-3 text-[#a8c7fa] text-sm font-medium">
                    <i class="fas fa-file-check"></i>
                    <span>Resume already uploaded</span>
                </div>
                {% endif %}
            </div>

            <div class="pt-6">
                <button type="submit" class="w-full gemini-gradient-bg text-white font-bold py-4 rounded-2xl shadow-lg uppercase tracking-widest text-sm transition-all hover:scale-[1.01]">
                    Update Profile
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}""")

# --- COMPANIES ---
update_file("companies/templates/companies/dashboard.html", """{% extends 'base.html' %}
{% block title %}Employer Console | PlacementAI{% endblock %}
{% block content %}
<div class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12">
    <div>
        <h1 class="text-4xl font-bold text-[#ffffff] mb-2">Employer <span class="gemini-gradient-text">Console</span></h1>
        <p class="text-[#c4c7c5]">Manage your recruitment pipeline efficiently</p>
    </div>
    <a href="{% url 'companies:create_job' %}" class="gemini-gradient-bg px-8 py-3.5 rounded-2xl font-bold uppercase tracking-widest text-xs shadow-lg flex items-center">
        <i class="fas fa-plus-circle mr-2"></i> Post Job
    </a>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
    {% for job in jobs %}
    <div class="glass-card rounded-[2rem] p-8 group flex flex-col h-full hover:border-[#a8c7fa]/30 transition-all">
        <div class="flex justify-between items-start mb-6">
            <h3 class="text-2xl font-bold text-[#ffffff] group-hover:text-[#a8c7fa] transition-colors leading-tight">{{ job.title }}</h3>
            <div class="bg-[#004a77]/30 text-[#a8c7fa] text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-full border border-[#a8c7fa]/20 shadow-sm">
                {{ job.applicant_count }} Active
            </div>
        </div>
        
        <p class="text-[#c4c7c5] text-sm mb-8 line-clamp-3 leading-relaxed flex-grow">
            {{ job.description }}
        </p>

        <div class="flex flex-wrap gap-2 mb-8">
            {% for skill in job.skills.all|slice:":3" %}
            <span class="px-3 py-1.5 bg-[#282a2c] text-[#e3e3e3] text-[10px] font-bold rounded-xl border border-[#444746] uppercase tracking-tighter">{{ skill.name }}</span>
            {% endfor %}
        </div>

        <div class="grid grid-cols-2 gap-3 pt-8 border-t border-[#444746]">
            <a href="{% url 'companies:job_applicants' job.id %}" class="text-center bg-[#444746] hover:bg-[#5f6368] text-[#ffffff] py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                Applicants
            </a>
            <a href="{% url 'companies:edit_job' job.id %}" class="text-center bg-[#282a2c] hover:bg-[#444746] text-[#c4c7c5] border border-[#444746] py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                Edit Post
            </a>
        </div>
    </div>
    {% empty %}
    <div class="col-span-full glass-card rounded-[3rem] p-24 text-center border-dashed border-2 border-[#444746]">
        <div class="text-6xl mb-8">
            <i class="fas fa-sparkles gemini-gradient-text opacity-40"></i>
        </div>
        <h3 class="text-2xl font-bold text-[#ffffff] mb-4">No job postings active</h3>
        <p class="text-[#c4c7c5] mb-10 max-w-md mx-auto">Your recruitment engine is idle. Post your first opportunity and let AI find your perfect match.</p>
        <a href="{% url 'companies:create_job' %}" class="inline-block px-12 py-4 gemini-gradient-bg text-white rounded-2xl font-bold uppercase tracking-widest text-xs shadow-xl">Start Hiring</a>
    </div>
    {% endfor %}
</div>
{% endblock %}""")

# --- ASSESSMENTS ---
update_file("assessments/templates/assessments/result.html", """{% extends 'base.html' %}
{% block title %}Assessment Submitted | PlacementAI{% endblock %}
{% block content %}
<div class="flex items-center justify-center min-h-[60vh] w-full">
    <div class="glass-card rounded-[2.5rem] p-12 max-w-xl mx-auto w-full text-center relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-green-500/5 rounded-full -mr-16 -mt-16 blur-3xl"></div>
        
        <div class="inline-flex items-center justify-center w-24 h-24 bg-[#004a77]/30 rounded-[2rem] border border-[#a8c7fa]/30 mb-8 animate-bounce">
            <i class="fas fa-check-double text-4xl text-[#a8c7fa]"></i>
        </div>
        
        <h2 class="text-4xl font-bold text-[#ffffff] mb-4">Assessment Complete</h2>
        <p class="text-[#c4c7c5] text-lg mb-10">Your responses have been securely transmitted to the evaluation engine.</p>
        
        <div class="bg-[#282a2c] border border-[#444746] rounded-2xl p-6 mb-10 text-left">
            <p class="text-[#ffffff] text-sm font-semibold mb-2 flex items-center"><i class="fas fa-info-circle mr-2 text-[#a8c7fa]"></i> Next Steps:</p>
            <ul class="text-[#8e918f] text-xs space-y-2 list-none">
                <li>• AI will analyze your coding and logical scores</li>
                <li>• Results will be shared with the employer within 24 hours</li>
                <li>• You'll receive a notification for the interview round</li>
            </ul>
        </div>

        <a href="{% url 'candidate_dashboard' %}" class="inline-block px-12 py-4 gemini-gradient-bg rounded-2xl text-white font-bold uppercase tracking-widest text-xs shadow-xl transition-all hover:scale-105 active:scale-95">
            Return to Dashboard
        </a>
    </div>
</div>
{% endblock %}""")

print("Gemini Design Batch Update Complete")
