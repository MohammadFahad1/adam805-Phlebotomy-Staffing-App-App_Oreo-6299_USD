from django.urls import path
from appointments import views

urlpatterns = [
    path('service-packages/', views.ServicePackageListView.as_view(), name='service-package-list'),
    path('create/', views.CreateAppointmentView.as_view(), name='appointment-create'),
    path('list/', views.AppointmentListView.as_view(), name='appointment-list'),
    path('detail/<int:pk>/', views.AppointmentDetailView.as_view(), name='appointment-detail'),
#     path('update/<int:pk>/', views.AppointmentUpdateView.as_view(), name='appointment-update'),
#     path('delete/<int:pk>/', views.AppointmentDeleteView.as_view(), name='appointment-delete'),
]