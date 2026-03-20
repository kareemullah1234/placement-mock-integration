import os, re

def migrate_tailwind_template(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if not body_match: return
        
    body_content = body_match.group(1).strip()
    
    # Strip existing navbars from these templates since base.html has one now
    body_content = re.sub(r'<nav.*?</nav>', '', body_content, flags=re.DOTALL|re.IGNORECASE)
    # Strip some absolute background divs if they conflict with base
    body_content = re.sub(r'<div class="absolute.*?w-96.*?</div>', '', body_content, flags=re.DOTALL|re.IGNORECASE)
    
    title = os.path.basename(filepath).replace('.html', '').replace('_', ' ').title()
    new_html = f"{{% extends 'base.html' %}}\n{{% block title %}}{title}{{% endblock %}}\n{{% block content %}}\n{body_content}\n{{% endblock %}}\n"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f'Migrated Tailwind Template: {filepath}')


def update_file(path, content):
    if not os.path.exists(path): return
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated: {path}")

# Migrate existing tailwind ones
targets = [
    'companies/templates/companies/create_job.html',
    'companies/templates/companies/job_list.html',
    'applications/templates/applications/job_applicants.html',
    'applications/templates/applications/choose_slot.html',
]
for t in targets:
    migrate_tailwind_template(t)

# Legacy template updates
# 1. Company Profile
update_file("companies/templates/companies/company_profile.html", """{% extends 'base.html' %}
{% block title %}Company Profile{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 max-w-2xl mx-auto w-full">
    <h2 class="text-3xl font-extrabold mb-6 tracking-tight text-white mb-8 border-b border-slate-700 pb-4">
        <i class="fas fa-building text-blue-500 mr-2"></i> Company Profile
    </h2>
    <form method="POST" class="space-y-6">
        {% csrf_token %}
        <div>
            <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Company Name</label>
            <input type="text" name="company_name" value="{{ profile.company_name }}" required class="form-input">
        </div>
        <div>
            <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Website</label>
            <input type="url" name="website" value="{{ profile.website }}" class="form-input" placeholder="https://domain.com">
        </div>
        <div>
            <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Description</label>
            <textarea name="description" rows="4" class="form-input">{{ profile.description }}</textarea>
        </div>
        <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl shadow-lg transition-all mt-4">
            Save Profile
        </button>
    </form>
</div>
{% endblock %}""")

# 2. Company Jobs
update_file("companies/templates/companies/company_jobs.html", """{% extends 'base.html' %}
{% block title %}My Jobs{% endblock %}
{% block content %}
<div class="mb-8 flex justify-between items-center border-b border-slate-700 pb-4">
    <h2 class="text-3xl font-extrabold tracking-tight text-white"><i class="fas fa-briefcase text-blue-500 mr-2"></i> My Posted Jobs</h2>
    <a href="{% url 'companies:create_job' %}" class="px-5 py-2.5 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold uppercase tracking-widest text-xs shadow-lg"><i class="fas fa-plus mr-2"></i> Post Job</a>
</div>
<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
    {% for job in jobs %}
    <div class="glass-card rounded-2xl p-6 hover:-translate-y-1 transition-transform">
        <div class="flex justify-between items-start mb-4">
            <h3 class="text-xl font-bold text-white">{{ job.title }}</h3>
            <span class="bg-blue-500/20 text-blue-400 text-xs font-bold px-3 py-1 rounded-full border border-blue-500/30">
                <i class="fas fa-users mr-1"></i> {{ job.applicant_count }} Applicants
            </span>
        </div>
        <div class="text-slate-400 text-sm mb-4 line-clamp-2">{{ job.description }}</div>
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
            <a href="{% url 'companies:edit_job' job.id %}" class="flex-1 text-center bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 border border-blue-500/20 py-2 rounded-lg text-sm font-semibold transition-colors">Edit Route / Rebuild</a>
        </div>
    </div>
    {% empty %}
    <p class="text-slate-500">No jobs posted yet.</p>
    {% endfor %}
</div>
{% endblock %}""")

# 3. Edit Job
update_file("companies/templates/companies/edit_job.html", """{% extends 'base.html' %}
{% block title %}Edit Job{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 max-w-2xl mx-auto w-full">
    <h2 class="text-3xl font-extrabold mb-6 tracking-tight text-white mb-8 border-b border-slate-700 pb-4">
        <i class="fas fa-edit text-blue-500 mr-2"></i> Edit Job
    </h2>
    <form method="POST" class="space-y-6">
        {% csrf_token %}
        <div>
            <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Job Title</label>
            <input type="text" name="title" value="{{ job.title }}" required class="form-input">
        </div>
        <div>
            <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Description</label>
            <textarea name="description" rows="4" required class="form-input">{{ job.description }}</textarea>
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Location</label>
                <input type="text" name="location" value="{{ job.location }}" required class="form-input">
            </div>
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Salary</label>
                <input type="number" name="salary" value="{{ job.salary }}" required class="form-input">
            </div>
        </div>
        <div class="flex items-center mt-4 mb-4">
            <input type="checkbox" name="is_active" {% if job.is_active %}checked{% endif %} id="active" class="h-4 w-4 bg-slate-900 border-slate-700 rounded text-blue-600 focus:ring-blue-500 mr-2">
            <label for="active" class="text-sm text-slate-300 font-medium">Job is Active</label>
        </div>
        <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-xl shadow-lg transition-all mt-4">
            Update Job
        </button>
    </form>
</div>
{% endblock %}""")

# 4. Companies Job Applicants
update_file("companies/templates/companies/job_applicants.html", """{% extends 'base.html' %}
{% block title %}Applicants - {{ job.title }}{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 w-full">
    <div class="flex justify-between items-center mb-6">
        <h2 class="text-2xl font-extrabold tracking-tight text-white">Applicants for: <span class="text-blue-400">{{ job.title }}</span></h2>
        <a href="{% url 'companies:company_dashboard' %}" class="text-sm text-slate-400 hover:text-white"><i class="fas fa-arrow-left mr-2"></i>Back</a>
    </div>

    <div class="overflow-x-auto rounded-xl border border-slate-700">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-800/80 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-700">
                    <th class="p-4">Candidate</th>
                    <th class="p-4">Email</th>
                    <th class="p-4">Status</th>
                    <th class="p-4">Resume</th>
                    <th class="p-4 text-center">Action</th>
                </tr>
            </thead>
            <tbody class="text-sm text-slate-300 divide-y divide-slate-700/50">
                {% for app in applications %}
                <tr class="hover:bg-slate-800/50 transition-colors">
                    <td class="p-4 font-semibold text-white">{{ app.candidate.user.username }}</td>
                    <td class="p-4">{{ app.candidate.user.email }}</td>
                    <td class="p-4">
                        <span class="px-3 py-1 bg-slate-800/80 rounded-full font-medium text-xs border border-slate-700 inline-block uppercase tracking-wider
                            {% if app.status == 'applied' %}text-yellow-400
                            {% elif app.status == 'shortlisted' %}text-blue-400
                            {% elif app.status == 'test_scheduled' %}text-purple-400
                            {% elif app.status == 'aptitude_passed' %}text-green-400
                            {% else %}text-slate-400{% endif %}">
                            <i class="fas fa-circle text-[8px] mr-1 mb-px"></i> {{ app.status|title }}
                        </span>
                    </td>
                    <td class="p-4">
                        {% if app.candidate.resume %}
                        <a href="{{ app.candidate.resume.url }}" target="_blank" class="text-blue-400 hover:text-blue-300"><i class="fas fa-file-pdf mr-1"></i> View</a>
                        {% else %}
                        <span class="text-slate-500">Not provided</span>
                        {% endif %}
                    </td>
                    <td class="p-4 text-center">
                        {% if app.status == 'applied' or app.status == 'shortlisted' %}
                        <a href="{% url 'companies:allow_test' app.id %}" class="inline-block px-3 py-1 bg-green-500/20 text-green-400 hover:bg-green-500/30 rounded border border-green-500/30 transition-colors text-xs font-bold uppercase tracking-wide"><i class="fas fa-check-circle mr-1"></i> Allow Test</a>
                        {% else %}
                        <span class="text-slate-500 text-xs">Test Allowed</span>
                        {% endif %}
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="5" class="p-8 text-center text-slate-500">No applicants yet.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}""")

print("refactor complete")
