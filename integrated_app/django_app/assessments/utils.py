import google.generativeai as genai
from django.conf import settings
import requests
import json
import re

genai.configure(api_key=settings.GEMINI_API_KEY)

JUDGE0_URL = "https://ce.judge0.com/submissions?base64_encoded=false&wait=true"


# -------------------------------
# Extract JSON safely from Gemini
# -------------------------------
def extract_json(text):

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        return json.loads(match.group())

    raise ValueError("Invalid JSON from Gemini")


# -------------------------------
# Generate Interview Questions
# -------------------------------
def generate_test_questions(skills):

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
Generate an aptitude test in JSON format.

Section 1:
5 aptitude questions (quantitative, logical, verbal).

Section 2:
5 skill based MCQ questions based on these skills:
{skills}

Section 3:
2 communication questions (descriptive).

Section 4:
Generate one coding interview question.

Rules:
- Do not add explanation
- Do not add markdown
- Do not add text outside JSON
- Ensure JSON is valid
- Always include 3 testcases

Return ONLY JSON in this format:

{{
  "aptitude":[
    {{
      "question":"",
      "options":["","","",""],
      "answer":""
    }}
  ],
  "skills":[
    {{
      "question":"",
      "options":["","","",""],
      "answer":""
    }}
  ],
  "communication":[
    {{
      "question":""
    }}
  ],
  "coding":[
    {{
      "question":"",
      "function_name":"",
      "input_description":"Explain what the input data contains",
      "example_input":"",
      "example_output":"",
      "test_cases":[
        {{"input":"","output":""}},
        {{"input":"","output":""}},
        {{"input":"","output":""}}
      ]
    }}
  ]
}}
"""

    response = model.generate_content(prompt)

    questions = extract_json(response.text)

    return questions


# -------------------------------
# Evaluate Code with Gemini
# -------------------------------
def evaluate_code_with_gemini(question, code, test_cases):

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
You are an automated coding evaluator.

Evaluate the candidate code and give ONLY a score from 0 to 10.

DO NOT explain anything.
DO NOT write sentences.
ONLY return a number.

Question:
{question}

Candidate Code:
{code}

Test Cases:
{test_cases}

Output example:
8
"""

    response = model.generate_content(prompt)

    text = response.text.strip()

    match = re.search(r"\d+", text)

    if match:
        return int(match.group())

    return 0


# -------------------------------
# Run Code using Judge0
# -------------------------------
def run_code(code, language_id, stdin, function_name):

    if not function_name:
        return "No function found"

    # ---------------- Python ----------------
    if language_id == 71:

        wrapped_code = f"""
import json

{code}

data = json.loads(input())

result = {function_name}(data)

if isinstance(result, (list, dict)):
    print(json.dumps(result))
else:
    print(result)
"""

    # ---------------- C++ ----------------
    elif language_id == 54:

        wrapped_code = f"""
#include <bits/stdc++.h>
using namespace std;

{code}

int main() {{

    string input;
    getline(cin,input);

    cout << {function_name}(input);

    return 0;
}}
"""

    # ---------------- Java ----------------
    elif language_id == 62:

        wrapped_code = f"""
import java.util.*;

public class Main {{

{code}

public static void main(String[] args) {{

    Scanner sc = new Scanner(System.in);

    String input = sc.nextLine();

    if(input.length() >= 2 && input.startsWith("\\"") && input.endsWith("\\"")) {{
        input = input.substring(1,input.length()-1);
    }}

    System.out.print({function_name}(input));
}}
}}
"""

    # ---------------- JavaScript ----------------
    elif language_id == 63:

        wrapped_code = f"""
{code}

const fs = require("fs");

let raw = fs.readFileSync(0,"utf8").trim();

let data = JSON.parse(raw);

let result = {function_name}(data);

if(typeof result === "object")
    console.log(JSON.stringify(result));
else
    console.log(result);
"""

    else:
        return "Unsupported language"


    payload = {
        "source_code": wrapped_code,
        "language_id": language_id,
        "stdin": str(stdin)
    }

    r = requests.post(JUDGE0_URL, json=payload)

    res = r.json()

    stdout = res.get("stdout")
    stderr = res.get("stderr")
    compile_output = res.get("compile_output")

    if stdout:
        return stdout.strip()

    if stderr:
        return stderr.strip()

    if compile_output:
        return compile_output.strip()

    return ""


# -------------------------------
# Normalize Outputs for Comparison
# -------------------------------
def normalize_output(value):

    if value is None:
        return ""

    value = str(value).strip()

    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]

    try:
        parsed = json.loads(value)
        return json.dumps(parsed, separators=(",", ":"))
    except:
        return value.replace(" ", "")