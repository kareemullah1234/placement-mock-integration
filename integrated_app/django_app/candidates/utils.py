import PyPDF2
import re


def extract_text_from_resume(file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception:
        pass
    return text.lower()


def match_skills(resume_text, job_skills):

    resume_text = resume_text.lower()
    resume_text = resume_text.replace("\n", " ")

    job_skills_list = [skill.strip().lower() for skill in job_skills.split(",")]

    matched_skills = []

    for skill in job_skills_list:

        pattern = r'\b' + re.escape(skill) + r'\b'

        if re.search(pattern, resume_text):
            matched_skills.append(skill)

    return matched_skills

import google.generativeai as genai
from django.conf import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def extract_skills_from_resume(resume_text):

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
    Extract the technical and professional skills from the following resume text.

    Return ONLY a comma separated list of skills.

    Resume:
    {resume_text}
    """

    response = model.generate_content(prompt)

    skills = response.text.strip()

    return skills