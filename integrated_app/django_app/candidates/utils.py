import PyPDF2
import re
from django.conf import settings

try:
    from google import genai  # type: ignore
except Exception:
    genai = None

_GEMINI_CLIENT = None


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


def _get_gemini_client():
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT

    if genai is None:
        raise RuntimeError(
            "Gemini SDK not installed. Install `google-genai` to use skill extraction."
        )

    api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("`GEMINI_API_KEY` is not set. Configure it in your environment or `.env`.")

    _GEMINI_CLIENT = genai.Client(api_key=api_key)
    return _GEMINI_CLIENT

def extract_skills_from_resume(resume_text):

    client = _get_gemini_client()

    prompt = f"""
    Extract the technical and professional skills from the following resume text.

    Return ONLY a comma separated list of skills.

    Resume:
    {resume_text}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    skills = (response.text or "").strip()

    return skills
