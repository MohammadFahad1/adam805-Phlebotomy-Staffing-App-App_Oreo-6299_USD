from django.urls import path
from dashboard import views

urlpatterns = [
    # Dashboard Home page
    path('home/', views.DashboardHomeView.as_view(), name='dashboard-home'),
    path('home/pending-registrations/', views.PendingRegistrationsAPIView.as_view(), name='pending-registrations'),
    path('home/user-details-for-approval/<int:user_id>', views.UserDetailForApproval.as_view(), name='user-detail-for-approval'),
    path('home/user-approval/<int:user_id>/', views.UserApprovalAPIView.as_view(), name='user-approval'),
    path('home/doc-approval/<int:user_id>/<int:document_id>/', views.UserDocumentApprovalAPIView.as_view(), name='user-document-approval'),
    path('home/pending-documents/', views.PendingDocumentsAPIView.as_view(), name='pending-documents'),
    path('home/suspend-unsuspend/<int:user_id>/', views.SuspendUserAccount.as_view(), name='suspend-unsuspend'),
    
    # Dashboard User Managements
    path('user-managements/', views.UserListAPIView.as_view(), name='user-managements'),
    path('user-managements/<int:user_id>/', views.UserManagementDetailView.as_view(), name='user-management-detail'),
    path('user-managements/<int:user_id>/edit/', views.UserManagementEditView.as_view(), name='user-management-edit'),
    
    # Dashboard Job Management
    path('job-managements/', views.JobManagementListView.as_view(), name='job-managements'),
    path('job-managements/<str:job_id>/', views.JobManagementDetailView.as_view(), name='job-management-detail'),
    path('job-managements/<str:job_id>/update-status/', views.JobStatusUpdateAPIView.as_view(), name='job-management-update-status'),
    path('job-managements/<str:job_id>/assign/', views.AssignPhlebotomistAPIView.as_view(), name='job-management-assign'),

    # Appointment Management
    path('appointment-managements/<int:appointment_id>/assign/', views.AdminAssignAppointmentUserView.as_view(), name='admin-assign-appointment-user'),
    path('appointment-managements/all-phlebotomists/', views.PhlebotomistListAPIView.as_view(), name='appointment-managements-all-phlebotomists'),

    # Dashboard Dispute Management
    path('dispute-statistics/', views.DisputeManagementStatisticsAPIView.as_view(), name='dispute-statistics'),
    path('disputes/', views.DisputeManagementListAPIView.as_view(), name='dispute-list'),
    path('disputes/<int:report_id>/', views.DisputeManagementDetailAPIView.as_view(), name='dispute-detail'),

    # Terms of Service Management
    path('terms-of-service/', views.PublicTermsOfServiceView.as_view(), name='terms-of-service'),
    path('admin/terms-of-service/', views.AdminTermsOfServiceListCreateView.as_view(), name='admin-terms-of-service-list-create'),
    path('admin/terms-of-service/<int:pk>/', views.AdminTermsOfServiceDetailView.as_view(), name='admin-terms-of-service-detail'),

    # Reviews Moderation
    path('reviews/', views.DashboardReviewsListAPIView.as_view(), name='dashboard-reviews-list'),
    path('reviews/<int:pk>/', views.DashboardReviewDetailAPIView.as_view(), name='dashboard-reviews-detail'),

    # Analytics & Reporting
    path('analytics-reporting/', views.AnalyticsReportingAPIView.as_view(), name='analytics-reporting'),

    # Job Matching
    path('job-matching/', views.ManualJobMatchingView.as_view(), name='manual-job-matching'),
    path('job-matching/available-users/', views.AvailablePhlebotomistsOrClientsForJobMatchingAPIView.as_view(), name='available-users-job-matching'),
    path('job-matching/available-users/<int:pk>/', views.AvailablePhlebotomistsOrClientsForJobMatchingDetailAPIView.as_view(), name='available-users-job-matching-detail'),

    # Payroll Management
    path('payroll/', views.AdminPayrollAPIView.as_view(), name='admin-payroll'),
    path('payroll/<str:pk>/', views.AdminPayrollDetailAPIView.as_view(), name='admin-payroll-detail'),

    # Terms & Conditions (Settings)
    path('admin/terms-and-conditions/', views.AdminTermsAndConditionsView.as_view(), name='admin-terms-and-conditions'),
    path('terms-and-conditions/', views.PublicTermsAndConditionsView.as_view(), name='public-terms-and-conditions'),

    # Service Packages 
    path('service-packages/', views.ServicePackagesAPIView.as_view(), name='service-packages'),
    path('service-packages/<int:package_id>/', views.ServicePackageDetailAPIView.as_view(), name='service-package-detail'),
    path('service-packages/features/', views.ServicePackageFeaturesAPIView.as_view(), name='service-package-features'),
    path('service-packages/features/<int:feature_id>/', views.ServicePackageFeatureDetailAPIView.as_view(), name='service-package-feature-detail'),
]
