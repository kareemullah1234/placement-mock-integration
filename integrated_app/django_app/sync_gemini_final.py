import os

def update_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated: {path}")

# --- CREATE JOB ---
update_file("companies/templates/companies/create_job.html", """{% extends 'base.html' %}
{% block title %}Post Job | PlacementAI{% endblock %}
{% block content %}
<div class="max-w-3xl mx-auto w-full">
    <div class="glass-card rounded-[2.5rem] p-10 sm:p-12 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-48 h-48 bg-[#004a77]/10 rounded-full blur-3xl -mr-24 -mt-24"></div>
        
        <div class="mb-12 border-b border-[#444746] pb-8 relative z-10">
            <h1 class="text-3xl font-bold text-[#ffffff] mb-2">Publish <span class="gemini-gradient-text">New Role</span></h1>
            <p class="text-[#c4c7c5]">Define your ideal candidate in seconds.</p>
        </div>

        <form method="POST" class="space-y-8 relative z-10">
            {% csrf_token %}
            <div>
                <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Position Title</label>
                <input type="text" name="title" required class="form-input" placeholder="e.g. Senior Software Architect">
            </div>

            <div>
                <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Job Description</label>
                <textarea name="description" rows="6" required class="form-input" placeholder="Outline the vision and day-to-day impact..."></textarea>
            </div>

            <div>
                <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Core Tech Stack</label>
                <input type="text" name="skills" required class="form-input" placeholder="React, Go, AWS, Kubernetes">
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-8">
                <div>
                    <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Work Location</label>
                    <input type="text" name="location" class="form-input" placeholder="San Francisco / Remote">
                </div>
                <div>
                    <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Annual Compensation ($)</label>
                    <input type="number" name="salary" required class="form-input" placeholder="185000">
                </div>
            </div>

            <div class="pt-8">
                <button type="submit" class="w-full gemini-gradient-bg text-white font-bold py-5 rounded-2xl shadow-xl uppercase tracking-[0.2em] text-sm transition-all hover:scale-[1.01]">
                    <i class="fas fa-sparkles mr-3"></i> Post Opportunity
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}""")

# --- EDIT JOB ---
update_file("companies/templates/companies/edit_job.html", """{% extends 'base.html' %}
{% block title %}Update Role | PlacementAI{% endblock %}
{% block content %}
<div class="max-w-3xl mx-auto w-full">
    <div class="glass-card rounded-[2.5rem] p-10 sm:p-12">
        <div class="mb-12 border-b border-[#444746] pb-8">
            <h1 class="text-3xl font-bold text-[#ffffff] mb-2">Edit <span class="gemini-gradient-text">Posting</span></h1>
            <p class="text-[#c4c7c5]">Refine the details for your open position.</p>
        </div>

        <form method="POST" class="space-y-8">
            {% csrf_token %}
            <div>
                <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Job Title</label>
                <input type="text" name="title" value="{{ job.title }}" required class="form-input">
            </div>
            <div>
                <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Detailed Description</label>
                <textarea name="description" rows="6" required class="form-input">{{ job.description }}</textarea>
            </div>
            <div class="grid grid-cols-2 gap-8">
                <div>
                    <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Location</label>
                    <input type="text" name="location" value="{{ job.location }}" required class="form-input">
                </div>
                <div>
                    <label class="block text-xs font-bold text-[#8e918f] uppercase tracking-widest mb-3 ml-1">Salary ($)</label>
                    <input type="number" name="salary" value="{{ job.salary }}" required class="form-input">
                </div>
            </div>
            <div class="flex items-center gap-4 bg-[#1e1f20] p-6 rounded-2xl border border-[#444746]">
                <input type="checkbox" name="is_active" {% if job.is_active %}checked{% endif %} id="active" class="h-5 w-5 rounded border-[#444746] bg-[#282a2c] text-[#a8c7fa] focus:ring-0">
                <label for="active" class="text-sm text-[#e3e3e3] font-medium">Currently accepting new applicants</label>
            </div>
            <div class="pt-8">
                <button type="submit" class="w-full gemini-gradient-bg text-white font-bold py-5 rounded-2xl shadow-xl uppercase tracking-[0.2em] text-sm transition-all">
                    Save Changes
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}""")

# --- JOB APPLICANTS (COMPANY SIDE) ---
update_file("companies/templates/companies/job_applicants.html", """{% extends 'base.html' %}
{% block title %}Applicants | PlacementAI{% endblock %}
{% block content %}
<div class="max-w-6xl mx-auto w-full">
    <div class="flex items-center justify-between mb-12">
        <div>
            <h1 class="text-3xl font-bold text-[#ffffff] mb-2">Review <span class="gemini-gradient-text">Talent</span></h1>
            <p class="text-[#c4c7c5]">Evaluating applicants for: <span class="font-bold text-[#ffffff]">{{ job.title }}</span></p>
        </div>
        <a href="{% url 'companies:company_dashboard' %}" class="px-6 py-3 bg-[#282a2c] hover:bg-[#444746] text-[#c4c7c5] rounded-xl border border-[#444746] text-xs font-bold uppercase tracking-widest transition-all">
            Back to Console
        </a>
    </div>

    <div class="glass-card rounded-[2.5rem] overflow-hidden border-[#444746]">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-[#282a2c] text-[10px] font-black uppercase tracking-[0.2em] text-[#8e918f] border-b border-[#444746]">
                        <th class="px-8 py-6">Candidate</th>
                        <th class="px-8 py-6">Status</th>
                        <th class="px-8 py-6">Resume</th>
                        <th class="px-8 py-6 text-right">Selection</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-[#444746]/50">
                    {% for app in applications %}
                    <tr class="hover:bg-[#1e1f20]/50 transition-colors">
                        <td class="px-8 py-8">
                            <div class="flex items-center gap-4">
                                <div class="w-10 h-10 bg-[#004a77]/30 rounded-full flex items-center justify-center text-[#a8c7fa] font-bold text-xs border border-[#a8c7fa]/20">
                                    {{ app.candidate.user.username|first|upper }}
                                </div>
                                <div>
                                    <p class="text-[#ffffff] font-bold">{{ app.candidate.user.username }}</p>
                                    <p class="text-[#8e918f] text-[10px]">{{ app.candidate.user.email }}</p>
                                </div>
                            </div>
                        </td>
                        <td class="px-8 py-8">
                            <span class="px-3 py-1 bg-[#1e1f20] border border-[#444746] rounded-full text-[9px] font-black uppercase tracking-widest
                                {% if app.status == 'applied' %}text-yellow-400
                                {% elif app.status == 'shortlisted' %}text-[#a8c7fa]
                                {% elif app.status == 'aptitude_passed' %}text-green-400
                                {% else %}text-[#c4c7c5]{% endif %}">
                                {{ app.status|title }}
                            </span>
                        </td>
                        <td class="px-8 py-8">
                            {% if app.candidate.resume %}
                            <a href="{{ app.candidate.resume.url }}" target="_blank" class="text-[#a8c7fa] hover:text-[#ffffff] transition-colors text-xs flex items-center gap-2 font-bold">
                                <i class="fas fa-file-pdf"></i> View PDF
                            </a>
                            {% else %}
                            <span class="text-[#8e918f] text-[10px] uppercase font-black">Missing</span>
                            {% endif %}
                        </td>
                        <td class="px-8 py-8 text-right">
                            {% if app.status == 'applied' or app.status == 'shortlisted' %}
                            <a href="{% url 'companies:allow_test' app.id %}" class="inline-block px-5 py-2.5 bg-[#a8c7fa]/10 hover:bg-[#a8c7fa] hover:text-[#131314] text-[#a8c7fa] border border-[#a8c7fa]/30 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
                                Authorize Test
                            </a>
                            {% else %}
                            <span class="text-[#8e918f] text-[10px] font-bold uppercase tracking-widest border border-[#444746] px-4 py-2 rounded-xl bg-[#282a2c]">In Assessment</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="4" class="px-8 py-20 text-center text-[#8e918f] text-sm font-bold uppercase tracking-widest">No candidates found for this position.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}""")

print("Final Template Synchronization Complete")
