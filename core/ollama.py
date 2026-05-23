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
    return f"""You are an expert ATS (Applicant Tracking System) analyst. Use markdown formatting in your response — use **bold** for important terms, ## for section headers, and - for bullet points.

IMPORTANT: You MUST refer to the user directly as "you" and "your" (e.g., "your resume", "your experience") rather than "the candidate" or "their". Address the user in a direct, personal tone.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Analyse the match and respond using this structure:

## Match Score
**Score: NN/100**  (replace NN with your numeric score, e.g. **Score: 72/100**)
[One sentence verdict on the overall fit]

## Summary
[2-3 sentences on overall alignment]

## Keywords Found ✓
- **[keyword]** — [where it appears in the resume]
- [repeat for all found keywords, aim for 5-10]

## Keywords Missing ✗
- **[keyword]** — [why it matters for this role]
- [repeat for all missing keywords, aim for 3-7]

## Suggestions to Improve Your Match
1. **[Specific action]** — [explanation of what to change and why]
2. **[Specific action]** — [explanation]
3. **[Specific action]** — [explanation]

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
    return f"""You are a brutally honest career advisor who has read thousands of job descriptions. Use markdown formatting — ## for section headers, **bold** for decoded phrases, and - for bullet points.

IMPORTANT: You MUST refer to the user directly as "you" and "your" rather than "the candidate" or "their". Address the user in a direct, personal tone.

JOB DESCRIPTION:
{jd_text}

Decode this job description. Translate the corporate language into plain honest English.

Use this exact format:

## Culture Read
[2-3 sentences on what this JD signals about the company culture and work environment]

## Decoded Phrases
- **"[exact phrase from JD]"** → [what it actually signals in plain English]
- **"[exact phrase]"** → [what it signals]
[repeat for 6-8 of the most revealing phrases]

## What They Really Want
1. **[Priority 1]** — [explanation]
2. **[Priority 2]** — [explanation]
3. **[Priority 3]** — [explanation]

## Compensation Signals
[What the JD reveals or deliberately hides about pay, stability, and growth]

Be honest but not cynical. Some phrases mean exactly what they say."""


def red_flags_prompt(jd_text):
    return f"""You are a career advisor helping the user spot warning signs in job descriptions. Use markdown formatting — ## for headers, **bold** for flagged phrases, and emoji indicators for severity.

IMPORTANT: You MUST refer to the user directly as "you" and "your" rather than "the candidate" or "their". Address the user in a direct, personal tone.

JOB DESCRIPTION:
{jd_text}

Analyse this JD for red flags. Use this exact format:

## Overall Verdict
**[🟢 GREEN / 🟡 YELLOW / 🔴 RED]** — [one sentence overall assessment]

## Flags Found

### 🔴 High Severity
[Include this section only if high severity flags exist]
- **"[exact phrase from JD]"**
  - *What it signals:* [honest explanation of what this typically means]
  - *Ask this in the interview:* "[specific question to probe this]"

### 🟡 Medium Severity
[Include this section only if medium severity flags exist]
- **"[exact phrase from JD]"**
  - *What it signals:* [explanation]
  - *Ask this in the interview:* "[question]"

### 🟢 Low Severity / Worth Noting
[Include this section only if low severity flags exist]
- **"[exact phrase from JD]"**
  - *What it signals:* [explanation]
  - *Ask this in the interview:* "[question]"
[continue for 3 to 5 flags total]

If there are genuinely no significant red flags say so clearly. Be calibrated, not everything is a problem."""


def interview_prep_prompt(resume_text, jd_text):
    return f"""You are an expert interview coach preparing the user for a specific role. Use markdown formatting — ## for question headers, **bold** for key points, and *italics* for tips.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

IMPORTANT: You MUST refer to the user directly as "you" and "your" (e.g., "your resume", "your experience") rather than "the candidate" or "their". Address the user in a direct, personal tone.

Generate the interview preparation guide. Use this exact structure:

## Topics to Study
Based on the key requirements and keywords in the job description, you should focus on studying the following areas before the interview:
- **[Topic/Keyword]** — [explanation of what to review and why it is critical for this role]
- [repeat for 3-5 key topics/keywords]

---

## Question 1
**[The interview question]**

*Why they'll ask this:* [one sentence on what the interviewer is probing]

**How to approach your answer:**
[2-3 sentences on how to answer well, referencing your actual resume experience where relevant]

---

## Question 2
[same format]

---

[continue through Question 6]

---

## Wildcard ⚡
**[One unexpected question you should prepare for]**

*Why this might come up:* [brief explanation]

Make every question specific to this role and to you. No generic questions."""


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