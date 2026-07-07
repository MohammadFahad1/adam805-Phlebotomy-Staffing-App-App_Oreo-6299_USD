from django.urls import path
from jobs import views

urlpatterns = [
    # Job Endpoints
    path('post/', views.JobCreateView.as_view(), name='job-create'),
]