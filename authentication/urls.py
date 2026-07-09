from django.urls import path
from authentication import views

urlpatterns = [
    # Registration Endpoints
    path('register/phlebotomist/', views.PhlebotomistRegistrationView.as_view(), name='phlebotomist-register'),
    path('register/client/', views.ClientRegistrationView.as_view(), name='client-register'),
    
    # Login Endpoint
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('account/delete/', views.AccountDeleteAPIView.as_view(), name='account-delete'),
    
    # Profile Update Endpoints
    path('profile/me/', views.ProfileAPIView.as_view(), name='my-profile'),
    path('profile/phlebotomist/update/', views.PhlebotomistProfileUpdateView.as_view(), name='phlebotomist-profile-update'),
    path('profile/client/update/', views.ClientProfileUpdateView.as_view(), name='client-profile-update'),
    path('profile/phlebotomist/', views.PhlebotomistProfileView.as_view(), name='phlebotomist-profile'),
    path('profile/client/', views.ClientProfileView.as_view(), name='client-profile'),
    
    # Forget Password Endpoints
    path('forget-password/', views.RequestForgetPasswordAPIView.as_view(), name='forget-password'),
    path('verify-otp/', views.VerifyForgetPasswordOTPAPIView.as_view(), name='verify-otp'),
    path('reset-password/', views.ResetPasswordAPIView.as_view(), name='reset-password'),
]
