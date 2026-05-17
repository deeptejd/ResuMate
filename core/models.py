from django.db import models

# Create your models here.
class MasterResume(models.Model):
    filename = models.CharField(max_length=255)
    raw_text = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename


class JobApplication(models.Model):
    job_title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    jd_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resume = models.ForeignKey(
        MasterResume,
        on_delete=models.SET_NULL,
        null=True,
        related_name='job_applications'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job_title} at {self.company}"


class Analysis(models.Model):
    job = models.OneToOneField(
        JobApplication,
        on_delete=models.CASCADE,
        related_name='analysis'
    )
    ats_score = models.IntegerField(null=True, blank=True)
    ats_match = models.TextField(blank=True, default='')
    cover_letter = models.TextField(blank=True, default='')
    jd_decode = models.TextField(blank=True, default='')
    red_flags = models.TextField(blank=True, default='')
    interview_prep = models.TextField(blank=True, default='')
    tailored_resume = models.TextField(blank=True, default='')
    resume_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis for {self.job}"

    def is_complete(self):
        return all([
            self.ats_match,
            self.cover_letter,
            self.jd_decode,
            self.red_flags,
            self.interview_prep,
        ])