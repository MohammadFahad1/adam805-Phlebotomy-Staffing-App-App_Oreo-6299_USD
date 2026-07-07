from phlebotomy_staffing.base import NewAPIView
from rest_framework.response import Response
from rest_framework import status
from dashboard import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from drf_yasg.utils import swagger_auto_schema
from authentication.serializers import EmptySerializer
from authentication.models import Client, Phlebotomist

class DashboardHomeView(NewAPIView):
    serializer_class = serializers.DashboardHomeSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    @swagger_auto_schema(tags=['Dashboard Endpoints'])
    def get(self, request):
        """
        **Get Dashboard Home Data**\n
        Retrieve data for the dashboard home page.\n
        
        **Response:**
        - **total_users**: Total number of users.
        - **pending_verifications**: Number of pending verifications.
        - **active_jobs**: Number of active jobs.
        - **revenue_this_month**: Revenue for the current month.
        - **pending_registrations_count**: Number of pending registrations.
        - **document_to_verify_count**: Number of documents to verify.
        - **recent_activities**: List of recent activities.
        - **jobs_completed_today**: Number of jobs completed today.
        - **average_rating**: Average rating.
        - **active_disputes**: Number of active disputes.
        - **response_time**: Response time.
        """
        return Response(self.serializer_class(self.request.user).data, status=status.HTTP_200_OK)

class PendingRegistrationsAPIView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    @swagger_auto_schema(tags=['Dashboard Endpoints'])
    def get(self, request):
        """
        **Get Pending Registrations**\n
        Retrieve a list of pending registrations for clients and phlebotomists.\n
        
        **Response:**
        - **total**: Total number of pending registrations.
        - **users**: List of pending registrations.
        
        **Example Response:**
        ```
        {
        "total": 2,
        "users": [
                {
                    "profile_picture": "http://localhost:8001/media/profile_pictures/fahad_Fc2dmEM.jpg",
                    "name": "Abrar Ahmed",
                    "role": "Phlebotomist",
                    "availability": "Available",
                    "distance": "2.5 miles",
                    "certification": "No Certification",
                    "experience": 6
                },
                {
                    "profile_picture": "http://localhost:8001/media/profile_pictures/vehicle_damage_unclear_B9g79tl.jpg",
                    "name": "Sami Nafis",
                    "role": "Client",
                    "availability": "Available",
                    "distance": "2.5 miles",
                    "certification": "No Certification",
                    "experience": null
                }
            ]
        }
        ```
        """
        phlebotomists = Phlebotomist.objects.filter(approved=False)
        clients = Client.objects.filter(is_approved=False)
        users = []
        for phlebotomist in phlebotomists:
            users.append({
                "profile_picture": request.build_absolute_uri(phlebotomist.user.profile_picture.url) if phlebotomist.user.profile_picture else None,
                "name": phlebotomist.user.full_name,
                "role": "Phlebotomist",
                "availability": "Available",
                "distance": "2.5 miles",
                "certification": "Certified Phlebotomist" if phlebotomist.documents.filter(document_name="license").exists() else "No Certification",
                "experience": phlebotomist.years_of_experience,
            })
        for client in clients:
            users.append({
                "profile_picture": request.build_absolute_uri(client.client.profile_picture.url) if client.client.profile_picture else None,
                "name": client.client.full_name,
                "role": "Client",
                "availability": "Available",
                "distance": "2.5 miles",
                "certification": "Certified Client" if client.documents.filter(document_name="license").exists() else "No Certification",
                "experience": None,
            })
        return Response({
            "total": len(users),
            "users": users
        }, status=status.HTTP_200_OK)


