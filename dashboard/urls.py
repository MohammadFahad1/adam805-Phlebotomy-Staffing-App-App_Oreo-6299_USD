from django.urls import path
from dashboard import views

urlpatterns = [
    # Dashboard Home page
    path('home/', views.DashboardHomeView.as_view(), name='dashboard-home'),
    path('home/pending-registrations/', views.PendingRegistrationsAPIView.as_view(), name='pending-registrations'),
]