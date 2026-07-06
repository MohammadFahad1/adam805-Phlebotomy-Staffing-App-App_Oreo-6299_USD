from django.urls import path
from authentication import views

urlpatterns = [
    # Registration Endpoints
    path('register/phlebotomist/', views.PhlebotomistRegistrationView.as_view(), name='phlebotomist-register'),
    path('register/client/', views.ClientRegistrationView.as_view(), name='client-register'),
    
    # Forget Password Endpoints
    path('forget-password/', views.RequestForgetPasswordAPIView.as_view(), name='forget-password'),
    path('verify-otp/', views.VerifyForgetPasswordOTPAPIView.as_view(), name='verify-otp'),
    path('reset-password/', views.ResetPasswordAPIView.as_view(), name='reset-password'),
]
