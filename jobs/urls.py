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
    path('client/jobs/<str:job_id>/invoice/', views.ClientJobInvoicePDFView.as_view(), name='client-job-invoice'),
    path('client/jobs/<str:job_id>/', views.ClientJobDetailAPIView.as_view(), name='client-job-detail'),
    path('client/jobs/<str:job_id>/pay/', views.ClientJobPayAPIView.as_view(), name='client-job-pay'),
    path('client/jobs/<str:job_id>/review/', views.CreateJobReviewAPIView.as_view(), name='client-job-review'),
    path('jobs/<str:job_id>/review/', views.CreateJobReviewAPIView.as_view(), name='job-review'),

    path('client/appointments/', views.ClientAppointmentListForHome.as_view(), name='client-appointments'),
    path('client/appointments/pending/', views.ClientPendingAppointmentsAPIView.as_view(), name='client-pending-appointments'),
    path('client/appointments/<int:pk>/', views.ClientAppointmentDetailAPIView.as_view(), name='client-appointment-detail'),
    path('client/phlebotomists/find/', views.ClientFindPhlebotomistAPIView.as_view(), name='client-find-phlebotomist'),
    path('client/phlebotomists/<int:user_id>/invite/', views.InvitePhlebotomistToTheJob.as_view(), name='invite-phlebotomist-to-job'),
    
    # Common Endpoints
    path('report-user/', views.ReportUserAPIView.as_view(), name='report-user'),
    
    # Phlebotomist Endpoints
    path('phlebotomist/jobs/', views.PhlebotomistAvailableJobsAPIView.as_view(), name='phlebotomist-available-jobs'),
    path('phlebotomist/applied/', views.PhlebotomistAppliedJobsAPIView.as_view(), name='phlebotomist-applied-jobs'),
    path('phlebotomist/jobs/history/', views.PhlebotomistJobHistoryAPIView.as_view(), name='phlebotomist-job-history'),
    path('phlebotomist/jobs/pending/', views.PhlebotomistPendingJobListAPIView.as_view(), name='phlebotomist-pending-jobs'),
    path('phlebotomist/jobs/<str:job_id>/', views.PhlebotomistJobDetailsAPIView.as_view(), name='phlebotomist-job-detail'),
    path('phlebotomist/jobs/<str:job_id>/complete/', views.PhlebotomistCompleteJobAPIView.as_view(), name='phlebotomist-complete-job'),
    path('phlebotomist/jobs/<str:job_id>/review/', views.CreateJobReviewAPIView.as_view(), name='phlebotomist-job-review'),
    path('phlebotomist/jobs/<str:job_id>/apply/', views.PhlebotomistJobApplyView.as_view(), name='phlebotomist-job-apply'),
    path('phlebotomist/jobs/<str:job_id>/accept/', views.PhlebotomistAcceptJobsAPIView.as_view(), name='phlebotomist-accept-job'),
    path('phlebotomist/jobs/<str:job_id>/reject/', views.PhlebotomistRejectJobsAPIView.as_view(), name='phlebotomist-reject-job'),
    path('phlebotomist/home/', views.PhlebotomistHomeAPIView.as_view(), name='phlebotomist-home'),
    path('phlebotomist/home/ratings-reviews/', views.PhlebotomistRatingsReviewsAPIView.as_view(), name='phlebotomist-ratings-reviews'),
    path('phlebotomist/clients/report/', views.PhlebotomistClientListToReportAPIView.as_view(), name='phlebotomist-clients-report'),
]

