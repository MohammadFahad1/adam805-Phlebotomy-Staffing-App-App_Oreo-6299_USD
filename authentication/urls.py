from django.urls import path
from authentication.views import PhlebotomistRegistrationView, ClientRegistrationView

urlpatterns = [
    path('register/phlebotomist/', PhlebotomistRegistrationView.as_view(), name='phlebotomist-register'),
    path('register/client/', ClientRegistrationView.as_view(), name='client-register'),
]
