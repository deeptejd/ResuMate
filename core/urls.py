from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('resume/upload/', views.upload_resume, name='upload_resume'),
    path('jobs/new/', views.new_job, name='new_job'),
    path('jobs/create/', views.create_job, name='create_job'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/stream/', views.stream_analysis, name='stream_analysis'),
    path('jobs/<int:job_id>/update-jd/', views.update_jd, name='update_jd'),
    path('jobs/<int:job_id>/resume/stream/', views.stream_tailored_resume, name='stream_tailored_resume'),
    path('jobs/<int:job_id>/resume/approve/', views.approve_resume, name='approve_resume'),
    path('jobs/<int:job_id>/export/pdf/', views.export_pdf, name='export_pdf'),
    path('jobs/<int:job_id>/export/md/', views.export_md, name='export_md'),
    path('jobs/<int:job_id>/export/cover-letter/', views.export_cover_letter, name='export_cover_letter'),
    path('jobs/<int:job_id>/delete/', views.delete_job, name='delete_job'),
    path('api/ollama-status/', views.ollama_status_api, name='ollama_status_api'),
]