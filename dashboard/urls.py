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
]