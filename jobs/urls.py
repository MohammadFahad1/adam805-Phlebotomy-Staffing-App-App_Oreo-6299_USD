from django.urls import path
from jobs import views

urlpatterns = [
    # Client Job Endpoints
    path('client/post/', views.JobCreateView.as_view(), name='job-create'),
    path('client/list/', views.JobListForClient.as_view(), name='client-job-list'),
    path('client/templates/', views.JobTemplateListForClient.as_view(), name='client-job-templates'),
    path('client/templates/<int:pk>/', views.JobTemplateDetailView.as_view(), name='client-job-template-detail'),
    path('client/home/', views.ClientHomeAPIView.as_view(), name='client-home'),
    path('client/home/ratings-reviews/', views.ClientRatingsReviewsAPIView.as_view(), name='client-ratings-reviews'),
    path('client/home/analytics/', views.ClientAppointmentTrendsAPIView.as_view(), name='client-analytics-trends'),
    path('client/jobs/history-billing/', views.ClientJobHistoryAndBillingAPIView.as_view(), name='client-jobs-history-billing'),

    path('client/appointments/', views.ClientAppointmentListForHome.as_view(), name='client-appointments'),
    path('client/appointments/pending/', views.ClientPendingAppointmentsAPIView.as_view(), name='client-pending-appointments'),
    path('client/appointments/<int:pk>/', views.ClientAppointmentDetailAPIView.as_view(), name='client-appointment-detail'),
    path('client/phlebotomists/find/', views.ClientFindPhlebotomistAPIView.as_view(), name='client-find-phlebotomist'),
    
    # Common Endpoints
    path('report-user/', views.ReportUserAPIView.as_view(), name='report-user'),
    
    # Phlebotomist Endpoints
    path('phlebotomist/jobs/', views.PhlebotomistAvailableJobsAPIView.as_view(), name='phlebotomist-available-jobs'),
    path('phlebotomist/applied/', views.PhlebotomistAppliedJobsAPIView.as_view(), name='phlebotomist-applied-jobs'),
    path('phlebotomist/jobs/pending/', views.PhlebotomistPendingJobListAPIView.as_view(), name='phlebotomist-pending-jobs'),
    path('phlebotomist/jobs/<str:job_id>/', views.PhlebotomistJobDetailsAPIView.as_view(), name='phlebotomist-job-detail'),
    path('phlebotomist/jobs/<str:job_id>/apply/', views.PhlebotomistJobApplyView.as_view(), name='phlebotomist-job-apply'),
    path('phlebotomist/jobs/<str:job_id>/accept/', views.PhlebotomistAcceptJobsAPIView.as_view(), name='phlebotomist-accept-job'),
    path('phlebotomist/jobs/<str:job_id>/reject/', views.PhlebotomistRejectJobsAPIView.as_view(), name='phlebotomist-reject-job'),
    path('phlebotomist/home/', views.PhlebotomistHomeAPIView.as_view(), name='phlebotomist-home'),
    path('phlebotomist/home/ratings-reviews/', views.PhlebotomistRatingsReviewsAPIView.as_view(), name='phlebotomist-ratings-reviews'),
]

