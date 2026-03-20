import os

def update_file(path, content):
    if not os.path.exists(path):
        print(f"Skipping {path}, does not exist.")
        return
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Updated: {path}")

# 1. Login Page
update_file("accounts/templates/accounts/login.html", """{% extends 'base.html' %}
{% block title %}Login | Placement Portal{% endblock %}
{% block content %}
<div class="flex items-center justify-center min-h-[70vh] w-full">
    <div class="w-full max-w-md glass-card rounded-3xl p-8 sm:p-10 relative z-10">
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-600/10 rounded-2xl border border-blue-500/20 mb-4 group">
                <i class="fas fa-rocket text-2xl text-blue-500 group-hover:scale-110 transition-transform duration-300"></i>
            </div>
            <h1 class="text-3xl font-extrabold text-white tracking-tight mb-2">Welcome Back</h1>
            <p class="text-slate-400 text-sm">Empowering your career journey together</p>
        </div>

        {% if error %}
        <div class="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-xl text-sm mb-6 flex items-center">
            <i class="fas fa-exclamation-circle mr-3"></i>
            {{ error }}
        </div>
        {% endif %}

        <form method="post" class="space-y-6">
            {% csrf_token %}
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Username</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-user-circle text-slate-500 group-focus-within:text-blue-500 transition-colors"></i>
                    </div>
                    <input type="text" name="username" required class="form-input pl-11" placeholder="jondoe23">
                </div>
            </div>

            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Password</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-lock text-slate-500 group-focus-within:text-blue-500 transition-colors"></i>
                    </div>
                    <input type="password" name="password" required class="form-input pl-11" placeholder="••••••••">
                </div>
            </div>

            <button type="submit" class="w-full bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold py-3.5 rounded-xl shadow-lg border border-blue-400/20 transform hover:-translate-y-0.5 transition-all duration-200 uppercase tracking-widest text-sm mt-4">
                Access Portal
            </button>
        </form>

        <div class="mt-8 pt-6 border-t border-slate-700/50 text-center">
            <p class="text-slate-400 text-sm">
                New to the platform? 
                <a href="{% url 'register' %}" class="text-blue-500 hover:text-blue-400 font-bold transition-colors ml-1">Create Account</a>
            </p>
        </div>
    </div>
</div>
{% endblock %}""")

# 2. Register Page
update_file("accounts/templates/accounts/register.html", """{% extends 'base.html' %}
{% block title %}Register | Placement Portal{% endblock %}
{% block content %}
<div class="flex items-center justify-center min-h-[70vh] w-full">
    <div class="w-full max-w-md glass-card rounded-3xl p-8 sm:p-10 relative z-10">
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-16 h-16 bg-purple-600/10 rounded-2xl border border-purple-500/20 mb-4 group">
                <i class="fas fa-user-plus text-2xl text-purple-500 group-hover:scale-110 transition-transform duration-300"></i>
            </div>
            <h1 class="text-3xl font-extrabold text-white tracking-tight mb-2">Create Account</h1>
            <p class="text-slate-400 text-sm">Join our community and jumpstart your career</p>
        </div>

        <form method="post" class="space-y-6">
            {% csrf_token %}
            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Username</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-id-card text-slate-500 group-focus-within:text-purple-500 transition-colors"></i>
                    </div>
                    <input type="text" name="username" required class="form-input pl-11 focus:!border-purple-500 focus:!shadow-purple-500/30" placeholder="jondoe23">
                </div>
            </div>

            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Email Address</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-envelope text-slate-500 group-focus-within:text-purple-500 transition-colors"></i>
                    </div>
                    <input type="email" name="email" required class="form-input pl-11 focus:!border-purple-500 focus:!shadow-purple-500/30" placeholder="jon@gmail.com">
                </div>
                <p class="mt-2 text-[10px] text-slate-500 font-medium tracking-wide">* Use Gmail/Yahoo for candidate, corporate for company role.</p>
            </div>

            <div>
                <label class="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 ml-1">Password</label>
                <div class="relative group">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fas fa-lock text-slate-500 group-focus-within:text-purple-500 transition-colors"></i>
                    </div>
                    <input type="password" name="password" required class="form-input pl-11 focus:!border-purple-500 focus:!shadow-purple-500/30" placeholder="••••••••">
                </div>
            </div>

            <button type="submit" class="w-full bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold py-3.5 rounded-xl shadow-lg border border-purple-400/20 transform hover:-translate-y-0.5 transition-all duration-200 uppercase tracking-widest text-sm mt-4">
                Start Your Career
            </button>
        </form>

        <div class="mt-8 pt-6 border-t border-slate-700/50 text-center">
            <p class="text-slate-400 text-sm">
                Already have an account? 
                <a href="{% url 'login' %}" class="text-purple-500 hover:text-purple-400 font-bold transition-colors ml-1">Sign In Now</a>
            </p>
        </div>
    </div>
</div>
{% endblock %}""")

# 3. Candidate Dashboard
update_file("candidates/templates/candidates/dashboard.html", """{% extends 'base.html' %}
{% load tz %}
{% block title %}Candidate Dashboard | Placement Portal{% endblock %}
{% block content %}
<div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
    <div class="glass-card rounded-2xl p-6 flex flex-col items-center justify-center text-center hover:-translate-y-1 transition-transform">
        <div class="w-16 h-16 bg-blue-600/10 rounded-full flex items-center justify-center text-blue-500 mb-4 border border-blue-500/20">
            <i class="fas fa-chart-line text-2xl"></i>
        </div>
        <h3 class="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Total Applied</h3>
        <p class="text-3xl font-extrabold text-white">{{ applications|length }}</p>
    </div>
    
    <div class="glass-card rounded-2xl p-6 flex flex-col items-center justify-center text-center hover:-translate-y-1 transition-transform">
        <div class="w-16 h-16 bg-purple-600/10 rounded-full flex items-center justify-center text-purple-500 mb-4 border border-purple-500/20">
            <i class="fas fa-tasks text-2xl"></i>
        </div>
        <h3 class="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Assessments Cleared</h3>
        <p class="text-3xl font-extrabold text-white">0</p>
    </div>

    <div class="glass-card rounded-2xl p-6 flex flex-col items-center justify-center text-center hover:-translate-y-1 transition-transform">
        <div class="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center text-green-500 mb-4 border border-green-500/20">
            <i class="fas fa-handshake text-2xl"></i>
        </div>
        <h3 class="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Interviews Scheduled</h3>
        <p class="text-3xl font-extrabold text-white">0</p>
    </div>
</div>

<h2 class="text-2xl font-extrabold tracking-tight text-white mb-6"><i class="fas fa-file-alt text-blue-500 mr-2"></i> Application Status</h2>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    {% for app in applications %}
    <div class="glass-card rounded-2xl p-6">
        <div class="flex justify-between items-start mb-4">
            <div>
                <h3 class="text-xl font-bold text-white">{{ app.job.title }}</h3>
                <p class="text-slate-400 text-sm flex items-center mt-1">
                    <i class="fas fa-building mr-2"></i> {{ app.job.company.company_name }}
                </p>
            </div>
            <span class="px-3 py-1 bg-slate-800/80 rounded-full font-bold text-xs border border-slate-700 tracking-wider uppercase
                {% if app.status == 'applied' %}text-yellow-400
                {% elif app.status == 'shortlisted' %}text-blue-400
                {% elif app.status == 'test_scheduled' %}text-purple-400
                {% elif app.status == 'aptitude_passed' %}text-green-400
                {% elif app.status == 'interview_scheduled' %}text-orange-400
                {% else %}text-slate-400{% endif %}">
                <i class="fas fa-circle text-[8px] mr-1 mb-px"></i> {{ app.status|title }}
            </span>
        </div>
        
        <div class="flex gap-4 mt-6">
            {% if app.status == 'applied' %}
                <a href="{% url 'upload_resume' app.job.id %}" class="flex-1 text-center py-2 bg-blue-600/10 text-blue-400 hover:bg-blue-600/20 border border-blue-500/20 rounded-lg text-xs font-bold uppercase tracking-widest transition-colors">
                    Upload Resume
                </a>
            {% elif app.status == 'test_scheduled' %}
                <a href="{% url 'assessments:start_test' app.id %}" class="flex-1 text-center py-2 bg-purple-600/10 text-purple-400 hover:bg-purple-600/20 border border-purple-500/20 rounded-lg text-xs font-bold uppercase tracking-widest transition-colors">
                    Start Test
                </a>
            {% elif app.status == 'aptitude_passed' %}
                <a href="{% url 'applications:choose_test_slot' app.id %}" class="flex-1 text-center py-2 bg-green-500/10 text-green-400 hover:bg-green-500/20 border border-green-500/20 rounded-lg text-xs font-bold uppercase tracking-widest transition-colors">
                    Choose Interview Slot
                </a>
            {% elif app.status == 'interview_scheduled' %}
                <a href="{% url 'interviews:candidate_dashboard' %}" class="flex-1 text-center py-2 bg-orange-500/10 text-orange-400 hover:bg-orange-500/20 border border-orange-500/20 rounded-lg text-xs font-bold uppercase tracking-widest transition-colors">
                    View Interview
                </a>
            {% else %}
                <button disabled class="flex-1 text-center py-2 bg-slate-800 text-slate-500 border border-slate-700 rounded-lg text-xs font-bold uppercase tracking-widest cursor-not-allowed">
                    Under Review
                </button>
            {% endif %}
        </div>
    </div>
    {% empty %}
    <div class="col-span-full glass-card rounded-3xl p-12 text-center border-dashed border-2 border-slate-700">
        <i class="fas fa-folder-open text-6xl text-slate-600 mb-4"></i>
        <h3 class="text-xl font-bold text-slate-300 mb-2">No Applications Yet</h3>
        <p class="text-slate-500 mb-6">Start applying for jobs to see your progress here.</p>
        <a href="{% url 'companies:job_list' %}" class="inline-block px-6 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-white font-bold uppercase tracking-widest text-xs shadow-lg">Browse Jobs</a>
    </div>
    {% endfor %}
</div>
{% endblock %}""")

# 4. Assessment Test Page
update_file("assessments/templates/assessments/test_page.html", """{% extends 'base.html' %}
{% block title %}Aptitude Test{% endblock %}
{% block content %}
<div class="glass-card rounded-3xl p-8 max-w-4xl mx-auto w-full mb-10">
    <div class="border-b border-slate-700 pb-4 mb-8 flex justify-between items-center">
        <h2 class="text-3xl font-extrabold tracking-tight text-white"><i class="fas fa-edit text-blue-500 mr-2"></i> Assessment Test</h2>
        <span class="px-4 py-1.5 bg-blue-600/20 text-blue-400 border border-blue-500/30 font-bold rounded-full text-xs uppercase tracking-widest animate-pulse">
            Live
        </span>
    </div>

    <form method="POST" action="{% url 'assessments:submit_test' application_id %}">
        {% csrf_token %}
        <input type="hidden" name="application_id" value="{{ application_id }}">

        {% if questions.aptitude %}
        <div class="mb-10">
            <h3 class="text-xl font-bold text-indigo-400 mb-6 uppercase tracking-widest flex items-center">
                <i class="fas fa-brain mr-2"></i> Section 1: Aptitude
            </h3>
            <div class="space-y-6">
                {% for q in questions.aptitude %}
                <div class="bg-slate-900/50 p-6 rounded-2xl border border-slate-700">
                    <p class="text-white font-medium mb-4 text-lg">{{ forloop.counter }}. {{ q.question }}</p>
                    <div class="space-y-3">
                        {% for option in q.options %}
                        <label class="flex items-center space-x-3 p-3 rounded-lg border border-slate-700 cursor-pointer hover:bg-slate-800 transition-colors">
                            <input type="radio" name="apt{{ forloop.parentloop.counter }}" value="{{ option }}" required class="h-4 w-4 text-blue-600 bg-slate-900 border-slate-600">
                            <span class="text-slate-300">{{ option }}</span>
                        </label>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if questions.skills %}
        <div class="mb-10">
            <h3 class="text-xl font-bold text-purple-400 mb-6 uppercase tracking-widest flex items-center">
                <i class="fas fa-tools mr-2"></i> Section 2: Technical Skills
            </h3>
            <div class="space-y-6">
                {% for q in questions.skills %}
                <div class="bg-slate-900/50 p-6 rounded-2xl border border-slate-700">
                    <p class="text-white font-medium mb-4 text-lg">{{ forloop.counter }}. {{ q.question }}</p>
                    <div class="space-y-3">
                        {% for option in q.options %}
                        <label class="flex items-center space-x-3 p-3 rounded-lg border border-slate-700 cursor-pointer hover:bg-slate-800 transition-colors">
                            <input type="radio" name="skill{{ forloop.parentloop.counter }}" value="{{ option }}" required class="h-4 w-4 text-purple-600 bg-slate-900 border-slate-600">
                            <span class="text-slate-300">{{ option }}</span>
                        </label>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if questions.communication %}
        <div class="mb-10">
            <h3 class="text-xl font-bold text-green-400 mb-6 uppercase tracking-widest flex items-center">
                <i class="fas fa-comments mr-2"></i> Section 3: Communication
            </h3>
            <div class="space-y-6">
                {% for q in questions.communication %}
                <div class="bg-slate-900/50 p-6 rounded-2xl border border-slate-700">
                    <p class="text-white font-medium mb-4 text-lg">{{ forloop.counter }}. {{ q.question }}</p>
                    <textarea name="comm{{ forloop.counter }}" required rows="4" class="form-input text-sm" placeholder="Write your response here..."></textarea>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        {% if questions.coding %}
        <div class="mb-10">
            <h3 class="text-xl font-bold text-pink-400 mb-6 uppercase tracking-widest flex items-center">
                <i class="fas fa-laptop-code mr-2"></i> Section 4: Coding Challenge
            </h3>
            {% for q in questions.coding %}
            <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-700 mb-6 shadow-xl">
                <p class="text-white font-medium mb-4 text-lg">{{ q.question }}</p>
                <div class="bg-slate-800 p-4 rounded-xl border border-slate-600 mb-6 text-sm font-mono text-slate-300">
                    <p class="mb-2"><span class="text-emerald-400 font-bold">Example Input:</span> <br>{{ q.example_input|safe }}</p>
                    <p><span class="text-rose-400 font-bold">Example Output:</span> <br>{{ q.example_output|safe }}</p>
                </div>

                <input type="hidden" id="testcases{{ forloop.counter }}" value='{{ q.test_cases|json_script:"testcases_json" }}'>

                <div class="flex justify-between items-center mb-4">
                    <label class="text-xs font-bold text-slate-400 uppercase tracking-widest">Select Language</label>
                    <select id="language{{ forloop.counter }}" onchange="setTemplate({{ forloop.counter }})" class="bg-slate-800 border-slate-600 text-white rounded-lg px-4 py-2 text-sm font-medium outline-none">
                        <option value="71">Python</option>
                        <option value="54">C++</option>
                        <option value="62">Java</option>
                        <option value="63">JavaScript</option>
                    </select>
                </div>

                <textarea id="code{{ forloop.counter }}" name="code{{ forloop.counter }}" required rows="12" class="w-full bg-[#1e1e1e] text-[#d4d4d4] p-4 rounded-xl border border-slate-700 font-mono text-sm leading-relaxed mb-4 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors" spellcheck="false"></textarea>

                <div class="flex items-center gap-4 mb-4">
                    <button type="button" onclick="runCode({{ forloop.counter }}, '{{ q.function_name }}')" class="px-6 py-2.5 bg-slate-700 hover:bg-slate-600 border border-slate-500 text-white rounded-lg text-xs font-bold uppercase tracking-widest flex items-center transition-colors">
                        <i class="fas fa-play mr-2"></i> Run Code
                    </button>
                    <span id="run-status-{{ forloop.counter }}" class="hidden text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full"></span>
                </div>

                <pre id="output{{ forloop.counter }}" class="bg-black/50 p-4 rounded-xl border border-slate-800 text-slate-300 font-mono text-xs whitespace-pre-wrap min-h-[60px]"></pre>
            </div>
            {% endfor %}
        </div>
        {% endif %}

        <div class="mt-8 pt-8 border-t border-slate-700">
            <button type="submit" class="w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-bold rounded-xl shadow-lg uppercase tracking-widest text-sm transition-all transform hover:-translate-y-0.5 w-full flex justify-center items-center">
                <i class="fas fa-paper-plane mr-2"></i> Submit Assessment
            </button>
        </div>
    </form>
</div>
{% endblock %}

{% block extra_js %}
<script>
let codingQuestions = null;
{% if questions.coding %}
codingQuestions = {{ questions.coding|safe }};
{% endif %}

function getCookie(name){
    let cookieValue=null;
    if(document.cookie && document.cookie!==''){
        const cookies=document.cookie.split(';');
        for(let i=0;i<cookies.length;i++){
            const cookie=cookies[i].trim();
            if(cookie.substring(0,name.length+1)===(name+'=')){
                cookieValue=decodeURIComponent(cookie.substring(name.length+1));
                break;
            }
        }
    }
    return cookieValue;
}

function getTemplate(language, functionName){
    if(language == 71){
        return "def " + functionName + "(data):\n    # Write your code here\n    pass\n";
    }
    if(language == 54){
        return "#include <vector>\n#include <string>\nusing namespace std;\nauto " + functionName + "(auto data){\n    // Write your code here\n}\n";
    }
    if(language == 62){
        return "public static int " + functionName + "(String data){\n    // Write your code here\n    return 0;\n}\n";
    }
    if(language == 63){
        return "function " + functionName + "(data){\n    // Write your code here\n}\n";
    }
}

window.onload = function(){
    if(!codingQuestions) return;
    const editors = document.querySelectorAll("textarea[id^='code']")
    editors.forEach((editor,index)=>{
        const functionName = codingQuestions[index].function_name
        editor.value = getTemplate(71,functionName)
    })
}

function setTemplate(i){
    const language = document.getElementById("language"+i).value
    const editor = document.getElementById("code"+i)
    const functionName = codingQuestions[i-1].function_name
    editor.value = getTemplate(language,functionName)
}

function runCode(i, functionName) {
    const code = document.getElementById("code" + i).value;
    const language = document.getElementById("language" + i).value;
    const testCases = codingQuestions[i-1].test_cases;
    
    const statusB = document.getElementById("run-status-" + i);
    statusB.className = "text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30 inline-block";
    statusB.innerHTML = "<i class='fas fa-spinner fa-spin mr-1'></i> Running...";

    fetch("/assessments/run-code/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({
            code: code,
            language: language,
            test_cases: testCases,
            function_name: functionName
        })
    })
    .then(res => res.json())
    .then(data => {
        let text = "";
        if(data.error){
            document.getElementById("output"+i).innerText = data.error;
            statusB.className = "text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 inline-block";
            statusB.innerText = "Error";
            return;
        }

        if(data.results){
            data.results.forEach(r=>{
                text += r + "\n";
            })
            text += "\nPassed: "+data.passed+"/"+data.total;
            
            if(data.passed === data.total) {
                statusB.className = "text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full bg-green-500/20 text-green-400 border border-green-500/30 inline-block";
                statusB.innerHTML = "<i class='fas fa-check mr-1'></i> All Passed";
            } else {
                statusB.className = "text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 inline-block";
                statusB.innerHTML = "<i class='fas fa-exclamation-triangle mr-1'></i> " + data.passed + "/" + data.total + " Passed";
            }
        }

        document.getElementById("output"+i).innerText = text;
    })
    .catch(err => {
        statusB.className = "text-xs font-bold uppercase tracking-wide px-3 py-1 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 inline-block";
        statusB.innerText = "Error occurred";
        document.getElementById("output"+i).innerText = err;
    });
}
</script>
{% endblock %}""")

print("Successfully updated standard template views!")
