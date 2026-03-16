import json
from django.conf import settings

try:
    from google import genai  # type: ignore
except Exception:
    genai = None

_GEMINI_CLIENT = None


def _get_gemini_client():
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is not None:
        return _GEMINI_CLIENT

    if genai is None:
        raise RuntimeError(
            "Gemini SDK not installed. Install `google-genai` to use aptitude question generation."
        )

    api_key = (getattr(settings, "GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError("`GEMINI_API_KEY` is not set. Configure it in your environment or `.env`.")

    _GEMINI_CLIENT = genai.Client(api_key=api_key)
    return _GEMINI_CLIENT


def generate_aptitude_questions(job_role, num_questions=5):

    client = _get_gemini_client()

    prompt = f"""
Generate {num_questions} APTITUDE multiple choice questions.

The questions should test:
- Logical reasoning
- Numerical ability
- Analytical thinking
- Pattern recognition

DO NOT generate technical or programming questions.

Return ONLY JSON in this format:

[
  {{
    "question": "",
    "options": ["", "", "", ""],
    "answer": ""
  }}
]
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text or ""

    import re
    text = re.sub(r"```json|```", "", text).strip()

    questions = json.loads(text)

    return questions
