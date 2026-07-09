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
]
