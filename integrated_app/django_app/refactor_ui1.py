import os, re

def update_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated: {path}")

# 1. candidate profile
update_file("candidates/templates/candidates/profile.html", """{% extends 'base.html' %}
{% block title %}Candidate Profile{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 max-w-2xl mx-auto w-full">
    <h2 class="text-3xl font-extrabold mb-6 tracking-tight text-white mb-8 border-b border-slate-700 pb-4">
        <i class="fas fa-user-edit text-blue-500 mr-2"></i> Edit Profile
    </h2>
    <form method="POST" enctype="multipart/form-data" class="space-y-6">
        {% csrf_token %}
        <div>
            <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Mobile Phone</label>
            <input type="text" name="phone" value="{{ candidate.phone }}" class="form-input" placeholder="+1 234 567 8900">
        </div>
        <div>
            <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Upload New Resume (PDF/DOCX)</label>
            <input type="file" name="resume" class="form-input !p-2 bg-slate-800">
        </div>
        {% if candidate.resume %}
        <div class="bg-blue-500/10 border border-blue-500/20 p-4 rounded-xl">
            <p class="text-sm font-medium text-blue-400"><i class="fas fa-file-pdf mr-2"></i> Current Resume Uploaded</p>
        </div>
        {% endif %}
        <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl shadow-lg transition-all mt-4">
            Save Profile
        </button>
    </form>
</div>
{% endblock %}""")

# 2. upload resume
update_file("candidates/templates/candidates/upload_resume.html", """{% extends 'base.html' %}
{% block title %}Upload Resume{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 max-w-xl mx-auto w-full text-center">
    <div class="inline-flex items-center justify-center w-20 h-20 bg-blue-600/10 rounded-3xl border border-blue-500/20 mb-6">
        <i class="fas fa-cloud-upload-alt text-4xl text-blue-500"></i>
    </div>
    <h2 class="text-3xl font-extrabold mb-2 text-white">Upload Resume</h2>
    <p class="text-slate-400 mb-8">Applying for: <strong class="text-white">{{ job.title }}</strong></p>
    
    <form method="post" enctype="multipart/form-data" class="space-y-6">
        {% csrf_token %}
        <div class="border-2 border-dashed border-slate-600 hover:border-blue-500 transition-colors rounded-2xl p-8 bg-slate-900/50">
            <input type="file" name="resume" required class="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-500/10 file:text-blue-400 hover:file:bg-blue-500/20 cursor-pointer">
        </div>
        <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold py-4 rounded-xl shadow-lg">
            Submit Application
        </button>
    </form>
</div>
{% endblock %}""")

# 3. candidates result
update_file("candidates/templates/candidates/result.html", """{% extends 'base.html' %}
{% block title %}Screening Result{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 max-w-2xl mx-auto w-full text-center">
    {% if match_score >= 50 %}
    <div class="inline-flex items-center justify-center w-20 h-20 bg-green-500/10 rounded-full border border-green-500/20 mb-6">
        <i class="fas fa-check text-4xl text-green-500"></i>
    </div>
    <h2 class="text-3xl font-extrabold text-white mb-2">Congratulations!</h2>
    <p class="text-green-400 font-medium mb-8 text-lg">You have been {{ status }}</p>
    {% else %}
    <div class="inline-flex items-center justify-center w-20 h-20 bg-red-500/10 rounded-full border border-red-500/20 mb-6">
        <i class="fas fa-times text-4xl text-red-500"></i>
    </div>
    <h2 class="text-3xl font-extrabold text-white mb-2">Not Selected</h2>
    <p class="text-red-400 font-medium mb-8 text-lg">{{ status }}</p>
    {% endif %}

    <div class="bg-slate-900/50 border border-slate-700/50 rounded-2xl p-6 text-left space-y-4 mb-8">
        <div>
            <span class="text-xs font-bold text-slate-500 uppercase tracking-widest">Required Skills</span>
            <p class="text-slate-300 mt-1">{{ required_skills|join:", " }}</p>
        </div>
        <div>
            <span class="text-xs font-bold text-slate-500 uppercase tracking-widest">Matched Skills</span>
            <p class="text-slate-300 mt-1">{% if matched_skills %}{{ matched_skills|join:", " }}{% else %}None detected{% endif %}</p>
        </div>
        <div>
            <span class="text-xs font-bold text-slate-500 uppercase tracking-widest">Match Score</span>
            <div class="flex items-center mt-2">
                <div class="flex-grow bg-slate-800 rounded-full h-2.5 mr-4">
                    <div class="bg-blue-500 h-2.5 rounded-full" style="width: {{ match_score }}%"></div>
                </div>
                <span class="text-blue-400 font-bold">{{ match_score }}%</span>
            </div>
        </div>
    </div>
    
    <a href="{% url 'candidate_dashboard' %}" class="px-6 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-xl text-white font-medium transition-colors">
        Back to Dashboard
    </a>
</div>
{% endblock %}""")

# 4. assessments result
update_file("assessments/templates/assessments/result.html", """{% extends 'base.html' %}
{% block title %}Assessment Submitted{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 max-w-xl mx-auto w-full text-center">
    <div class="inline-flex items-center justify-center w-20 h-20 bg-blue-600/10 rounded-full border border-blue-500/20 mb-6">
        <i class="fas fa-paper-plane text-4xl text-blue-500"></i>
    </div>
    <h2 class="text-3xl font-extrabold text-white mb-4">Test Submitted</h2>
    
    <div class="bg-slate-900/50 border border-slate-700 rounded-2xl p-6 mb-8">
        <p class="text-slate-300 text-lg mb-2">Your test has been submitted successfully.</p>
        <p class="text-slate-500 text-sm">Our team will review your results and you will be notified shortly.</p>
    </div>

    <a href="{% url 'candidate_dashboard' %}" class="inline-block px-8 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-medium shadow-lg transition-all">
        Back to Dashboard
    </a>
</div>
{% endblock %}""")

# 5. companies dashboard
update_file("companies/templates/companies/dashboard.html", """{% extends 'base.html' %}
{% block title %}Company Dashboard{% endblock %}
{% block content %}
<div class="mb-8 flex justify-between items-center border-b border-slate-700 pb-4">
    <h2 class="text-3xl font-extrabold tracking-tight text-white"><i class="fas fa-building text-blue-500 mr-2"></i> Company Dashboard</h2>
    <a href="{% url 'companies:create_job' %}" class="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold uppercase tracking-widest text-xs shadow-lg flex items-center shadow-blue-500/20"><i class="fas fa-plus mr-2"></i> Post New Job</a>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {% for job in jobs %}
    <div class="glass-card rounded-2xl p-6 hover:-translate-y-1 transition-transform">
        <div class="flex justify-between items-start mb-4">
            <h3 class="text-xl font-bold text-white">{{ job.title }}</h3>
            <span class="bg-blue-500/20 text-blue-400 text-xs font-bold px-3 py-1 rounded-full border border-blue-500/30">
                <i class="fas fa-users mr-1"></i> {{ job.applicant_count }} Applicants
            </span>
        </div>
        <div class="text-slate-400 text-sm mb-4 line-clamp-2">
            {{ job.description }}
        </div>
        <div class="flex items-center text-xs text-slate-500 space-x-4 mb-6 uppercase tracking-widest font-bold">
            <span><i class="fas fa-map-marker-alt"></i> {{ job.location }}</span>
            <span><i class="fas fa-dollar-sign"></i> {{ job.salary }}</span>
        </div>
        <div class="flex flex-wrap gap-2 mb-6">
            {% for skill in job.skills.all %}
            <span class="px-2.5 py-1 bg-slate-800 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700">{{ skill.name }}</span>
            {% endfor %}
        </div>
        <div class="flex space-x-3 pt-4 border-t border-slate-700/50">
            <a href="{% url 'companies:job_applicants' job.id %}" class="flex-1 text-center bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/20 py-2 rounded-lg text-sm font-semibold transition-colors">View Applicants</a>
            <a href="{% url 'companies:edit_job' job.id %}" class="flex-1 text-center bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-600 py-2 rounded-lg text-sm font-semibold transition-colors">Edit</a>
        </div>
    </div>
    {% empty %}
    <div class="col-span-full glass-card rounded-3xl p-12 text-center border-dashed border-2 border-slate-700">
        <i class="fas fa-folder-open text-6xl text-slate-600 mb-4"></i>
        <h3 class="text-xl font-bold text-slate-300 mb-2">No active jobs</h3>
        <p class="text-slate-500 mb-6">You haven't posted any job openings yet.</p>
        <a href="{% url 'companies:create_job' %}" class="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-medium shadow-lg">Create First Job</a>
    </div>
    {% endfor %}
</div>
{% endblock %}""")

print("Successfully overwrote templates!")
