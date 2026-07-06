from django.urls import path
from authentication.views import PhlebotomistRegistrationView

urlpatterns = [
    path('register/phlebotomist/', PhlebotomistRegistrationView.as_view(), name='phlebotomist-register'),
]
