from django.urls import path
from appointments import views

urlpatterns = [
    path('service-packages/', views.ServicePackageListView.as_view(), name='service-package-list'),
    path('create/', views.CreateAppointmentView.as_view(), name='appointment-create'),
    path('list/', views.AppointmentListView.as_view(), name='appointment-list'),
    path('detail/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
    
    # Client Endpoints
    path('client/appointments/<int:appointment_id>/invite/', views.ClientInvitePhlebotomistView.as_view(), name='client-invite-phlebotomist'),
    
    # Patient Screen Endpoints
    path('patients/', views.PatientListView.as_view(), name='patient-list'),
    path('patient-appointment-detail/<int:pk>/', views.PatientAppointmentDetailView.as_view(), name='patient-appointment-detail'),
    
    # Payment Webhook
    path('stripe/webhook/', views.StripeWebhookView.as_view(), name='stripe-webhook'),
    path('payment-success/', views.PaymentSuccessView.as_view(), name='payment-success'),
    path('payment-cancel/', views.PaymentCancelView.as_view(), name='payment-cancel'),
    
    # Wallet Endpoints
    path('wallet/balance/', views.WalletBalanceView.as_view(), name='wallet-balance'),
    path('wallet/payout-request/', views.PayoutRequestView.as_view(), name='wallet-payout-request'),
]