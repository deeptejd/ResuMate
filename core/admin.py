from django.contrib import admin
from .models import MasterResume, JobApplication, Analysis

# Register your models here.
admin.site.register(MasterResume)
admin.site.register(JobApplication)
admin.site.register(Analysis)