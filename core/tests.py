from django.test import TestCase
from django.urls import reverse
from .models import JobApplication
from . import ollama as ol

class DashboardViewTestCase(TestCase):
    def test_dashboard_renders_with_filters(self):
        # Create a sample job application to ensure jobs block is rendered
        JobApplication.objects.create(
            job_title="Software Engineer",
            company="Google",
            jd_text="Looking for a Python Developer..."
        )
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="jobSearch"')
        self.assertContains(response, 'id="filterCompany"')
        self.assertContains(response, 'id="filterScore"')
        self.assertContains(response, 'id="filterStatus"')
        self.assertContains(response, 'id="sortJobs"')
        self.assertContains(response, 'id="btnResetFilters"')
        self.assertContains(response, 'id="noMatchingJobs"')

class OllamaPromptTestCase(TestCase):
    def test_interview_prep_prompt_contains_study_topics(self):
        prompt = ol.interview_prep_prompt("My Resume", "Python Developer JD")
        self.assertIn("Topics to Study", prompt)
        self.assertIn("Based on the key requirements and keywords in the job description", prompt)

class ExportCoverLetterTestCase(TestCase):
    def test_export_cover_letter_pdf(self):
        job = JobApplication.objects.create(
            job_title="Writer",
            company="Medium",
            jd_text="Write stories..."
        )
        # Create Analysis with cover letter content
        from .models import Analysis
        Analysis.objects.create(
            job=job,
            cover_letter="This is a test cover letter content."
        )
        response = self.client.get(reverse('export_cover_letter', args=[job.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

