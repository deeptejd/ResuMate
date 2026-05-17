import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import MasterResume, JobApplication, Analysis
from . import ollama as ol

_ATS_SCORE_PATTERNS = (
    r'(?i)\*{0,2}Score:\s*(\d{1,3})\s*/\s*100',  # **Score: 75/100**
    r'(?i)SCORE:\s*(\d{1,3})',                     # legacy SCORE: 75
)


def parse_ats_score(text):
    """Extract the 0–100 ATS match score from model output."""
    for pattern in _ATS_SCORE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 100:
                return score
    return None


def dashboard(request):
    try:
        resume = MasterResume.objects.filter(is_active=True).latest('uploaded_at')
    except MasterResume.DoesNotExist:
        resume = None

    jobs = JobApplication.objects.select_related('analysis').order_by('-created_at')

    return render(request, 'core/dashboard.html', {
        'resume': resume,
        'jobs': jobs,
    })


@require_POST
def upload_resume(request):
    if not request.FILES.get('resume'):
        messages.error(request, 'No file was selected.')
        return redirect('dashboard')

    uploaded_file = request.FILES['resume']

    try:
        from .parsers import extract_resume_text
        text = extract_resume_text(uploaded_file)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('dashboard')

    if len(text.strip()) < 100:
        messages.error(
            request,
            'Could not extract enough text from this file. '
            'Make sure it is not a scanned image PDF.'
        )
        return redirect('dashboard')

    MasterResume.objects.update(is_active=False)
    MasterResume.objects.create(
        filename=uploaded_file.name,
        raw_text=text,
        is_active=True,
    )
    messages.success(request, f'Resume uploaded: {uploaded_file.name}')
    return redirect('dashboard')


def new_job(request):
    try:
        resume = MasterResume.objects.filter(is_active=True).latest('uploaded_at')
    except MasterResume.DoesNotExist:
        messages.error(request, 'Please upload your resume before adding a job.')
        return redirect('dashboard')

    return render(request, 'core/new_job.html', {'resume': resume})


@require_POST
def create_job(request):
    job_title = request.POST.get('job_title', '').strip()
    company = request.POST.get('company', '').strip()
    jd_text = request.POST.get('jd_text', '').strip()

    if not job_title or not company or not jd_text:
        messages.error(request, 'All fields are required.')
        return redirect('new_job')

    try:
        resume = MasterResume.objects.filter(is_active=True).latest('uploaded_at')
    except MasterResume.DoesNotExist:
        messages.error(request, 'Please upload your resume first.')
        return redirect('dashboard')

    job = JobApplication.objects.create(
        job_title=job_title,
        company=company,
        jd_text=jd_text,
        resume=resume,
    )

    return redirect('job_detail', job_id=job.id)


def job_detail(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)

    try:
        analysis = Analysis.objects.get(job=job)
        if analysis.ats_match and analysis.ats_score is None:
            score = parse_ats_score(analysis.ats_match)
            if score is not None:
                analysis.ats_score = score
                analysis.save(update_fields=['ats_score', 'updated_at'])
        needs_analysis = not analysis.is_complete()
    except Analysis.DoesNotExist:
        analysis = None
        needs_analysis = True

    return render(request, 'core/job_detail.html', {
        'job': job,
        'analysis': analysis,
        'needs_analysis': json.dumps(needs_analysis),
        'job_id': job.id,
    })


def stream_analysis(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    analysis, _ = Analysis.objects.get_or_create(job=job)
    model = ol.get_model_name()

    tabs = [
        ('match',  'ats_match',      ol.ats_match_prompt(job.resume.raw_text, job.jd_text)),
        ('cover',  'cover_letter',   ol.cover_letter_prompt(job.resume.raw_text, job.jd_text)),
        ('decode', 'jd_decode',      ol.jd_decode_prompt(job.jd_text)),
        ('flags',  'red_flags',      ol.red_flags_prompt(job.jd_text)),
        ('prep',   'interview_prep', ol.interview_prep_prompt(job.resume.raw_text, job.jd_text)),
    ]

    def event_stream():
        for tab_key, field_name, prompt in tabs:
            yield f"event: tab_start\ndata: {json.dumps({'tab': tab_key})}\n\n"
            full_text = ""
            try:
                for token in ol.stream_prompt(prompt, model):
                    full_text += token
                    yield f"event: token\ndata: {json.dumps({'tab': tab_key, 'chunk': token})}\n\n"
            except Exception as e:
                error_msg = f"\n\n[Error during generation: {str(e)}]"
                full_text += error_msg
                yield f"event: token\ndata: {json.dumps({'tab': tab_key, 'chunk': error_msg})}\n\n"

            setattr(analysis, field_name, full_text)

            if tab_key == 'match':
                score = parse_ats_score(full_text)
                if score is not None:
                    analysis.ats_score = score

            analysis.save()
            yield f"event: tab_complete\ndata: {json.dumps({'tab': tab_key})}\n\n"

        yield f"event: analysis_complete\ndata: {{}}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def stream_tailored_resume(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    analysis = get_object_or_404(Analysis, job=job)
    model = ol.get_model_name()
    prompt = ol.tailored_resume_prompt(
        job.resume.raw_text,
        job.jd_text,
        analysis.ats_match,
    )

    def event_stream():
        full_text = ""
        try:
            for token in ol.stream_prompt(prompt, model):
                full_text += token
                yield f"event: token\ndata: {json.dumps({'chunk': token})}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
            return

        analysis.tailored_resume = full_text
        analysis.resume_approved = False
        analysis.save()
        yield f"event: complete\ndata: {{}}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@require_POST
def approve_resume(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    analysis = get_object_or_404(Analysis, job=job)
    analysis.resume_approved = True
    analysis.save()
    return JsonResponse({'ok': True})


@require_POST
def update_jd(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    jd_text = request.POST.get('jd_text', '').strip()
    if not jd_text:
        messages.error(request, 'Job description cannot be empty.')
        return redirect('job_detail', job_id=job_id)

    job.jd_text = jd_text
    job.save()

    try:
        analysis = Analysis.objects.get(job=job)
        analysis.ats_match = ''
        analysis.cover_letter = ''
        analysis.jd_decode = ''
        analysis.red_flags = ''
        analysis.interview_prep = ''
        analysis.tailored_resume = ''
        analysis.resume_approved = False
        analysis.ats_score = None
        analysis.save()
    except Analysis.DoesNotExist:
        pass

    messages.success(request, 'Job description updated. Analysis has been reset.')
    return redirect('job_detail', job_id=job_id)


def export_pdf(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    analysis = get_object_or_404(Analysis, job=job)

    if not analysis.tailored_resume or not analysis.resume_approved:
        messages.error(request, 'No approved tailored resume to export.')
        return redirect('job_detail', job_id=job_id)

    from .exporters import generate_pdf
    pdf_bytes = generate_pdf(job, analysis)

    filename = f"{job.company}_{job.job_title}_resume.pdf".replace(' ', '_')
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def export_md(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    analysis = get_object_or_404(Analysis, job=job)

    if not analysis.tailored_resume or not analysis.resume_approved:
        messages.error(request, 'No approved tailored resume to export.')
        return redirect('job_detail', job_id=job_id)

    from .exporters import generate_markdown
    md_content = generate_markdown(job, analysis)

    filename = f"{job.company}_{job.job_title}_resume.md".replace(' ', '_')
    response = HttpResponse(md_content, content_type='text/markdown')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# TODO: add export to PDF and MD for cover letter as well
def export_cover_letter(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    analysis = get_object_or_404(Analysis, job=job)

    if not analysis.cover_letter:
        messages.error(request, 'No cover letter to export.')
        return redirect('job_detail', job_id=job_id)

    filename = f"{job.company}_{job.job_title}_cover_letter.txt".replace(' ', '_')
    response = HttpResponse(analysis.cover_letter, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@require_POST
def delete_job(request, job_id):
    job = get_object_or_404(JobApplication, id=job_id)
    job.delete()
    messages.success(request, f'Job deleted.')
    return redirect('dashboard')