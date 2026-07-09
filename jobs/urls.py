from django.urls import path
from jobs import views

urlpatterns = [
    # Client Job Endpoints
    path('client/post/', views.JobCreateView.as_view(), name='job-create'),
    path('client/list/', views.JobListForClient.as_view(), name='client-job-list'),
    path('client/templates/', views.JobTemplateListForClient.as_view(), name='client-job-templates'),
    path('client/templates/<int:pk>/', views.JobTemplateDetailView.as_view(), name='client-job-template-detail'),
    
    # Phlebotomist Endpoints
    path('phlebotomist/jobs/', views.PhlebotomistAvailableJobsAPIView.as_view(), name='phlebotomist-available-jobs'),
    path('phlebotomist/applied/', views.PhlebotomistAppliedJobsAPIView.as_view(), name='phlebotomist-applied-jobs'),
    path('phlebotomist/jobs/pending/', views.PhlebotomistPendingJobListAPIView.as_view(), name='phlebotomist-pending-jobs'),
    path('phlebotomist/jobs/<str:job_id>/', views.PhlebotomistJobDetailsAPIView.as_view(), name='phlebotomist-job-detail'),
    path('phlebotomist/jobs/<str:job_id>/apply/', views.PhlebotomistJobApplyView.as_view(), name='phlebotomist-job-apply'),
]