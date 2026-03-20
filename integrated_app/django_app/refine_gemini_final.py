import os

def update_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated: {path}")

# --- ASSESSMENTS TEST PAGE ---
update_file("assessments/templates/assessments/test_page.html", """{% extends 'base.html' %}
{% block title %}Assessment | PlacementAI{% endblock %}
{% block content %}
<div class="max-w-5xl mx-auto w-full mb-20">
    <div class="glass-card rounded-[2.5rem] p-8 sm:p-12 mb-10 overflow-hidden relative">
        <div class="absolute top-0 right-0 w-64 h-64 bg-[#004a77]/10 rounded-full -mr-32 -mt-32 blur-3xl"></div>
        
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-12 border-b border-[#444746] pb-8 relative z-10">
            <div>
                <h1 class="text-3xl font-bold text-[#ffffff] mb-2">Technical <span class="gemini-gradient-text">Assessment</span></h1>
                <p class="text-[#c4c7c5]">Showcase your skills through this multi-stage evaluation.</p>
            </div>
            <div class="flex items-center gap-3">
                <span class="px-4 py-2 bg-[#1e1f20] border border-[#a8c7fa]/30 text-[#a8c7fa] rounded-full text-[10px] font-black uppercase tracking-widest animate-pulse">
                    Live Session
                </span>
            </div>
        </div>

        <form method="POST" action="{% url 'assessments:submit_test' application_id %}" id="assessmentForm">
            {% csrf_token %}
            <input type="hidden" name="application_id" value="{{ application_id }}">

            {% if questions.aptitude %}
            <div class="mb-16">
                <h3 class="text-sm font-black text-[#a8c7fa] mb-8 uppercase tracking-[0.2em] flex items-center">
                    <span class="w-8 h-8 bg-[#004a77]/30 rounded-lg flex items-center justify-center mr-3 text-xs">01</span>
                    Aptitude & Logic
                </h3>
                <div class="space-y-8">
                    {% for q in questions.aptitude %}
                    <div class="bg-[#282a2c]/50 p-8 rounded-3xl border border-[#444746] hover:border-[#a8c7fa]/20 transition-all">
                        <p class="text-[#ffffff] font-medium mb-6 text-lg leading-relaxed">{{ forloop.counter }}. {{ q.question }}</p>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {% for option in q.options %}
                            <label class="flex items-center p-4 rounded-2xl border border-[#444746] cursor-pointer hover:bg-[#1e1f20] hover:border-[#a8c7fa]/40 transition-all group">
                                <input type="radio" name="apt{{ forloop.parentloop.counter }}" value="{{ option }}" required class="w-5 h-5 border-[#444746] bg-[#1e1f20] text-[#a8c7fa] focus:ring-offset-0 focus:ring-1 focus:ring-[#a8c7fa]">
                                <span class="ml-4 text-[#c4c7c5] group-hover:text-[#ffffff] transition-colors text-sm">{{ option }}</span>
                            </label>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if questions.skills %}
            <div class="mb-16">
                <h3 class="text-sm font-black text-[#d3e3fd] mb-8 uppercase tracking-[0.2em] flex items-center">
                    <span class="w-8 h-8 bg-[#004a77]/30 rounded-lg flex items-center justify-center mr-3 text-xs">02</span>
                    Technical Knowledge
                </h3>
                <div class="space-y-8">
                    {% for q in questions.skills %}
                    <div class="bg-[#282a2c]/50 p-8 rounded-3xl border border-[#444746] hover:border-[#d3e3fd]/20 transition-all">
                        <p class="text-[#ffffff] font-medium mb-6 text-lg leading-relaxed">{{ forloop.counter }}. {{ q.question }}</p>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {% for option in q.options %}
                            <label class="flex items-center p-4 rounded-2xl border border-[#444746] cursor-pointer hover:bg-[#1e1f20] hover:border-[#d3e3fd]/40 transition-all group">
                                <input type="radio" name="skill{{ forloop.parentloop.counter }}" value="{{ option }}" required class="w-5 h-5 border-[#444746] bg-[#1e1f20] text-[#d3e3fd] focus:ring-offset-0 focus:ring-1 focus:ring-[#d3e3fd]">
                                <span class="ml-4 text-[#c4c7c5] group-hover:text-[#ffffff] transition-colors text-sm">{{ option }}</span>
                            </label>
                            {% endfor %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if questions.communication %}
            <div class="mb-16">
                <h3 class="text-sm font-black text-[#a8c7fa] mb-8 uppercase tracking-[0.2em] flex items-center">
                    <span class="w-8 h-8 bg-[#004a77]/30 rounded-lg flex items-center justify-center mr-3 text-xs">03</span>
                    Communication
                </h3>
                <div class="space-y-8">
                    {% for q in questions.communication %}
                    <div class="bg-[#282a2c]/50 p-8 rounded-3xl border border-[#444746]">
                        <p class="text-[#ffffff] font-medium mb-6 text-lg">{{ forloop.counter }}. {{ q.question }}</p>
                        <textarea name="comm{{ forloop.counter }}" required rows="5" class="form-input text-sm leading-relaxed" placeholder="Type your detailed response here..."></textarea>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% endif %}

            {% if questions.coding %}
            <div class="mb-16">
                <h3 class="text-sm font-black text-[#d3e3fd] mb-8 uppercase tracking-[0.2em] flex items-center">
                    <span class="w-8 h-8 bg-[#004a77]/30 rounded-lg flex items-center justify-center mr-3 text-xs">04</span>
                    Coding Challenge
                </h3>
                {% for q in questions.coding %}
                <div class="bg-[#1e1f20] rounded-[2rem] border border-[#444746] p-8 mb-10 overflow-hidden relative">
                    <div class="absolute top-0 right-0 p-4 opacity-10">
                        <i class="fas fa-code text-6xl"></i>
                    </div>
                    
                    <div class="relative z-10">
                        <p class="text-xl font-bold text-[#ffffff] mb-8">{{ q.question }}</p>
                        
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
                            <div class="bg-[#282a2c] p-6 rounded-2xl border border-[#444746]">
                                <span class="text-[10px] font-black text-[#a8c7fa] uppercase tracking-widest block mb-3">Input Example</span>
                                <pre class="text-[#e3e3e3] font-mono text-sm whitespace-pre-wrap">{{ q.example_input|safe }}</pre>
                            </div>
                            <div class="bg-[#282a2c] p-6 rounded-2xl border border-[#444746]">
                                <span class="text-[10px] font-black text-emerald-400 uppercase tracking-widest block mb-3">Expected Output</span>
                                <pre class="text-[#e3e3e3] font-mono text-sm whitespace-pre-wrap">{{ q.example_output|safe }}</pre>
                            </div>
                        </div>

                        <div class="flex items-center justify-between gap-4 mb-4">
                            <div class="flex items-center gap-3">
                                <i class="fas fa-terminal text-[#8e918f] text-sm"></i>
                                <span class="text-xs font-bold text-[#8e918f] uppercase tracking-widest">Environment</span>
                            </div>
                            <select id="language{{ forloop.counter }}" onchange="setTemplate({{ forloop.counter }})" class="bg-[#282a2c] border-[#444746] text-[#ffffff] rounded-xl px-4 py-2 text-xs font-bold outline-none cursor-pointer hover:border-[#a8c7fa]/50 transition-all">
                                <option value="71">Python 3</option>
                                <option value="54">C++ 17</option>
                                <option value="62">Java 11</option>
                                <option value="63">Node.js</option>
                            </select>
                        </div>

                        <div class="rounded-2xl border border-[#444746] overflow-hidden focus-within:border-[#a8c7fa]/50 transition-all mb-6">
                            <textarea id="code{{ forloop.counter }}" name="code{{ forloop.counter }}" required rows="14" class="w-full bg-[#131314] text-[#e3e3e3] p-6 font-mono text-sm leading-relaxed outline-none" spellcheck="false" placeholder="// Start coding..."></textarea>
                        </div>

                        <div class="flex flex-col sm:flex-row items-center justify-between gap-6">
                            <div class="flex items-center gap-4">
                                <button type="button" onclick="runCode({{ forloop.counter }}, '{{ q.function_name }}')" class="px-8 py-3 bg-[#282a2c] hover:bg-[#444746] text-[#ffffff] border border-[#444746] rounded-xl text-xs font-bold uppercase tracking-widest transition-all flex items-center">
                                    <i class="fas fa-play mr-2 text-emerald-400"></i> Run Console
                                </button>
                                <div id="run-status-{{ forloop.counter }}" class="hidden px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border"></div>
                            </div>
                        </div>

                        <div id="output-container-{{ forloop.counter }}" class="mt-6 hidden">
                            <pre id="output{{ forloop.counter }}" class="bg-[#131314] p-6 rounded-2xl border border-[#444746] text-[#c4c7c5] font-mono text-xs whitespace-pre-wrap min-h-[100px]"></pre>
                        </div>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <div class="pt-10 border-t border-[#444746] flex justify-center">
                <button type="submit" class="w-full max-w-md px-12 py-5 gemini-gradient-bg text-white font-bold rounded-2xl shadow-2xl uppercase tracking-[0.2em] text-sm transition-all hover:scale-[1.02] active:scale-95 flex items-center justify-center">
                    <i class="fas fa-cloud-upload-alt mr-3"></i> Finish & Submit
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    let codingQuestions = null;
    {% if questions.coding %}
    codingQuestions = {{ questions.coding|safe }};
    {% endif %}

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getTemplate(language, functionName) {
        if (language == 71) return "def " + functionName + "(data):\\n    # Your logic here\\n    pass\\n";
        if (language == 54) return "#include <iostream>\\n#include <vector>\\nusing namespace std;\\n\\nauto " + functionName + "(auto data) {\\n    // Your logic here\\n}\\n";
        if (language == 62) return "public class Solution {\\n    public int " + functionName + "(String data) {\\n        // Your logic here\\n        return 0;\\n    }\\n}\\n";
        if (language == 63) return "function " + functionName + "(data) {\\n    // Your logic here\\n}\\n";
        return "";
    }

    window.onload = function() {
        if(!codingQuestions) return;
        document.querySelectorAll("textarea[id^='code']").forEach((editor, index) => {
            editor.value = getTemplate(71, codingQuestions[index].function_name);
        });
    }

    function setTemplate(i) {
        const lang = document.getElementById("language" + i).value;
        const editor = document.getElementById("code" + i);
        editor.value = getTemplate(lang, codingQuestions[i-1].function_name);
    }

    function runCode(i, functionName) {
        const code = document.getElementById("code" + i).value;
        const lang = document.getElementById("language" + i).value;
        const status = document.getElementById("run-status-" + i);
        const output = document.getElementById("output" + i);
        const container = document.getElementById("output-container-" + i);

        container.classList.remove('hidden');
        status.classList.remove('hidden');
        status.className = "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-[#1e1f20] border-[#a8c7fa]/30 text-[#a8c7fa]";
        status.innerHTML = "<i class='fas fa-circle-notch fa-spin mr-2'></i> Processing";

        fetch("/assessments/run-code/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken")
            },
            body: JSON.stringify({
                code: code,
                language: lang,
                test_cases: codingQuestions[i-1].test_cases,
                function_name: functionName
            })
        })
        .then(res => res.json())
        .then(data => {
            if(data.error) {
                output.innerText = data.error;
                status.className = "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-red-500/10 border-red-500/30 text-red-400";
                status.innerText = "Error";
                return;
            }
            
            let resultText = "";
            (data.results || []).forEach(r => resultText += r + "\\n");
            resultText += "\\nResult: " + data.passed + " / " + data.total + " Test Cases Passed";
            output.innerText = resultText;
            
            if(data.passed === data.total) {
                status.className = "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-green-500/10 border-green-500/30 text-green-400";
                status.innerText = "All Tests Cleared";
            } else {
                status.className = "px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border bg-orange-500/10 border-orange-500/30 text-orange-400";
                status.innerText = data.passed + "/" + data.total + " Passed";
            }
        })
        .catch(err => {
            status.innerText = "Network Error";
            output.innerText = err;
        });
    }
</script>
{% endblock %}""")

# --- COMPANIES JOB LIST ---
update_file("companies/templates/companies/job_list.html", """{% extends 'base.html' %}
{% block title %}Explore Careers | PlacementAI{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto w-full pb-20">
    <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-8 mb-16">
        <div class="max-w-2xl">
            <h1 class="text-5xl font-bold text-[#ffffff] mb-4 tracking-tight">Shape the <span class="gemini-gradient-text">Future</span></h1>
            <p class="text-[#c4c7c5] text-lg">Browse curated high-impact opportunities from revolutionary companies around the globe.</p>
        </div>
        <div class="flex flex-wrap gap-4">
            <div class="relative group">
                <i class="fas fa-search absolute left-5 top-1/2 -translate-y-1/2 text-[#8e918f] text-sm group-focus-within:text-[#a8c7fa] transition-colors"></i>
                <input type="text" placeholder="Search positions..." class="form-input pl-12 pr-6 py-4 rounded-2xl w-80 bg-[#1e1f20]">
            </div>
            <button class="px-6 py-4 bg-[#282a2c] rounded-2xl border border-[#444746] text-[#e3e3e3] hover:bg-[#444746] transition-all">
                <i class="fas fa-sliders-h"></i>
            </button>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {% for job in jobs %}
        <div class="glass-card rounded-[2.5rem] p-8 flex flex-col hover:border-[#a8c7fa]/40 hover:-translate-y-2 transition-all group overflow-hidden relative">
            <div class="absolute top-0 right-0 w-32 h-32 bg-[#004a77]/10 rounded-full blur-3xl -mr-16 -mt-16"></div>
            
            <div class="flex items-center justify-between mb-8">
                <div class="w-14 h-14 bg-[#282a2c] rounded-2xl flex items-center justify-center border border-[#444746] shadow-sm">
                    <i class="fas fa-briefcase text-xl text-[#a8c7fa]"></i>
                </div>
                <span class="text-[10px] font-black uppercase tracking-[0.2em] text-[#8e918f]">Active Now</span>
            </div>

            <h3 class="text-2xl font-bold text-[#ffffff] mb-2 group-hover:text-[#a8c7fa] transition-colors line-clamp-1">{{ job.title }}</h3>
            <p class="text-[#c4c7c5] text-sm font-medium mb-6 flex items-center">
                {{ job.company.company_name }}
            </p>

            <div class="flex flex-wrap gap-2 mb-8">
                <span class="px-3 py-1.5 bg-[#1e1f20] text-[#8e918f] text-[10px] font-black rounded-xl border border-[#444746] tracking-widest uppercase">{{ job.location }}</span>
                <span class="px-3 py-1.5 bg-[#1e1f20] text-emerald-400/80 text-[10px] font-black rounded-xl border border-emerald-500/20 tracking-widest uppercase">${{ job.salary }}</span>
            </div>

            <div class="mt-auto flex items-center gap-4">
                <a href="{% url 'companies:job_list' %}" class="flex-1 text-center py-4 bg-[#282a2c] hover:bg-[#444746] text-[#ffffff] border border-[#444746] rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all">
                    Details
                </a>
                <a href="{% url 'applications:apply_job' job.id %}" class="flex-1 text-center py-4 gemini-gradient-bg text-white rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-lg hover:shadow-[#a8c7fa]/10">
                    Apply Fast
                </a>
            </div>
        </div>
        {% empty %}
        <div class="col-span-full py-20 text-center glass-card rounded-[3rem] border-dashed">
            <p class="text-[#8e918f] font-bold uppercase tracking-widest text-sm">No positions matched your search</p>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}""")

print("Final Refinement Complete")
