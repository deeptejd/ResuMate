import json
import requests
from django.conf import settings


def get_model_name():
    try:
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags",
            timeout=5
        )
        if response.status_code == 200:
            models = [m['name'] for m in response.json().get('models', [])]
            gemma = next(
                (m for m in models if 'gemma' in m.lower()), None
            )
            if gemma:
                return gemma
    except Exception:
        pass
    return settings.OLLAMA_MODEL


def check_connection():
    try:
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags",
            timeout=5
        )
        if response.status_code == 200:
            models = [m['name'] for m in response.json().get('models', [])]
            gemma = next(
                (m for m in models if 'gemma' in m.lower()), None
            )
            return {
                'ok': True,
                'model': gemma or settings.OLLAMA_MODEL,
                'has_gemma': gemma is not None,
            }
    except Exception:
        pass
    return {'ok': False, 'model': None, 'has_gemma': False}


def stream_prompt(prompt, model=None):
    if model is None:
        model = get_model_name()
    response = requests.post(
        f"{settings.OLLAMA_BASE_URL}/api/chat",
        json={
            "model": model,
            "stream": True,
            "messages": [{"role": "user", "content": prompt}],
        },
        stream=True,
        timeout=300,
    )
    response.raise_for_status()
    for line in response.iter_lines():
        if line:
            try:
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
            except json.JSONDecodeError:
                continue


def ats_match_prompt(resume_text, jd_text):
    return f"""You are an expert ATS (Applicant Tracking System) analyst.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Analyse the match between this resume and job description. Use this exact format:

SCORE: [a single number from 0 to 100]
VERDICT: [one sentence summary of the fit]
SUMMARY: [2 to 3 sentences on overall alignment]

KEYWORDS FOUND:
- [keyword from JD that is present in the resume]
- [add all relevant ones, aim for 5 to 10]

KEYWORDS MISSING:
- [important JD keyword that is absent from the resume]
- [add all relevant ones, aim for 3 to 7]

SUGGESTIONS:
1. [specific and actionable rewrite suggestion]
2. [specific and actionable rewrite suggestion]
3. [specific and actionable rewrite suggestion]

Be honest. Do not fabricate experience."""


def cover_letter_prompt(resume_text, jd_text):
    return f"""You are a senior career coach writing a tailored cover letter.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

First silently read the tone of the JD (formal, startup casual, technical, creative) and match it exactly in your writing.

Rules:
- Do not open with "I am writing to apply" or "I am excited to apply" or any variation
- Open with something specific that shows genuine understanding of the company or role
- Reference 2 to 3 real achievements from the resume that map directly to JD requirements
- Write exactly 3 paragraphs, no more, no filler sentences
- End with a confident and specific call to action

Write only the cover letter. No preamble. No explanation. No "here is your cover letter"."""


def jd_decode_prompt(jd_text):
    return f"""You are a brutally honest career advisor who has read thousands of job descriptions.

JOB DESCRIPTION:
{jd_text}

Decode this job description. Translate the corporate language into plain honest English.

Use this exact format:

CULTURE READ:
[2 to 3 sentences on what this JD reveals about the company culture and work environment]

DECODED PHRASES:
"[exact phrase from the JD]" -> [what it actually signals]
[repeat for 6 to 8 of the most revealing phrases in the JD]

WHAT THEY REALLY WANT:
[The 3 actual priorities behind the listed requirements]

COMPENSATION SIGNALS:
[What the JD reveals or deliberately hides about pay, stability, and growth]

Be honest but not cynical. Some phrases mean exactly what they say."""


def red_flags_prompt(jd_text):
    return f"""You are a career advisor helping candidates spot warning signs in job descriptions.

JOB DESCRIPTION:
{jd_text}

Analyse this JD for red flags. Use this exact format:

VERDICT: [GREEN or YELLOW or RED] - [one sentence overall assessment]

FLAG 1:
SEVERITY: [HIGH or MEDIUM or LOW]
PHRASE: "[exact text from the JD]"
SIGNAL: [what this pattern typically means in practice]
ASK THIS: [a question to probe this concern in the interview]

FLAG 2:
SEVERITY: [HIGH or MEDIUM or LOW]
PHRASE: "[exact text from the JD]"
SIGNAL: [what this pattern typically means in practice]
ASK THIS: [a question to probe this concern in the interview]

[continue for 3 to 5 flags total]

If there are genuinely no significant red flags say so clearly. Be calibrated, not everything is a problem."""


def interview_prep_prompt(resume_text, jd_text):
    return f"""You are an expert interview coach preparing a candidate for a specific role.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Generate exactly 6 interview questions tailored to this specific role and this specific candidate. Use this exact format:

Q1: [The interview question]
WHY: [One sentence on what the interviewer is really probing]
APPROACH: [2 to 3 sentences on how to answer well, referencing their actual resume experience where possible]

Q2:
[same format]

[continue through Q6]

WILDCARD: [One unexpected question they should prepare for]

Make every question specific to this role and this candidate. No generic questions."""


def tailored_resume_prompt(resume_text, jd_text, ats_analysis):
    return f"""You are an expert resume writer. Rewrite the resume below to be optimally tailored for the job description provided.

MASTER RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

ATS ANALYSIS CONTEXT:
{ats_analysis}

Rules:
- Do not fabricate any experience, skills, achievements, or qualifications that are not in the original resume
- Reorganise and emphasise existing experience to match the priorities of the JD
- Incorporate missing keywords naturally only where the candidate genuinely has that experience
- Strengthen bullet points to use the language and metrics the JD values
- Format the output as a clean resume using markdown: use # for name, ## for section headers, and - for bullet points
- Include these sections in order: Summary, Experience, Skills, Education, and any other sections present in the original
- Every line should earn its place

Write only the complete rewritten resume in markdown. No preamble. No explanation. No commentary."""