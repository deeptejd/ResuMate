from django.test import TestCase
from django.urls import reverse
from .models import JobApplication

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
