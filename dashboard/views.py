from phlebotomy_staffing.base import NewAPIView
from rest_framework.response import Response
from rest_framework import status
from dashboard import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from authentication.serializers import EmptySerializer
from authentication.models import Client, Phlebotomist
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class DashboardHomeView(NewAPIView):
    serializer_class = serializers.DashboardHomeSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    @swagger_auto_schema(tags=['Dashboard Endpoints'])
    def get(self, request):
        """
        **Get Dashboard Home Data - Admin Only**\n
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
        **Get Pending Registrations - Admin Only**\n
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
                    "id": 1,
                    "profile_picture": "http://localhost:8001/media/profile_pictures/fahad_Fc2dmEM.jpg",
                    "name": "Abrar Ahmed",
                    "role": "Phlebotomist",
                    "availability": "Available",
                    "distance": "2.5 miles",
                    "certification": "No Certification",
                    "experience": 6
                },
                {
                    "id": 2,
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
        phlebotomists = Phlebotomist.objects.filter(Q(approved=False) | Q(approved=None)).select_related('user')
        clients = Client.objects.filter(Q(is_approved=False) | Q(is_approved=None)).select_related('client')
        users = []
        for phlebotomist in phlebotomists:
            users.append({
                "id": phlebotomist.user.id,
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
                "id": client.client.id,
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

class UserDetailForApproval(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'patch']
    
    @swagger_auto_schema(tags=['Dashboard Endpoints'])
    def get(self, request, user_id):
        """
        **Get User Detail for Approval - Admin Only**\n
        Retrieve detailed information about a specific user (client or phlebotomist) for approval purposes.\n
        
        **Parameters:**
        - **user_id**: The ID of the user to retrieve details for.
        
        **Response:**
        - **user_detail**: Detailed information about the user.
        
        **Example Response**:
        ```Json
        {
            "id": 4,
            "profile_picture": "http://localhost:8001/media/profile_pictures/vehicle_damage_unclear_B9g79tl.jpg",
            "name": "Sami Nafis",
            "email": "nafis@gmail.com",
            "phone_number": "01772211521",
            "gender": "male",
            "dob": "1996-04-20",
            "role": "client",
            "registration_date": "2026-07-07",
            "experience": null,
            "address": "Bir Sreshtho AK Khandokar Road, Mohakhali, Dhaka, Bangladesh, 1212",
            "is_approved": false,
            "uploaded_documents": [
                {
                    "id": 1,
                    "document_name": "business_license",
                    "file_name": "vehicle_damage_Hq03rqP.jpeg",
                    "file_size": "9.1 KB",
                    "document_file": "http://localhost:8001/media/client_documents/vehicle_damage_Hq03rqP.jpeg",
                    "uploaded_on": "July 07, 2026",
                    "approved": false
                },
                {
                    "id": 2,
                    "document_name": "identification",
                    "file_name": "2222_p5phAuO.jpg",
                    "file_size": "1.2 MB",
                    "document_file": "http://localhost:8001/media/client_documents/2222_p5phAuO.jpg",
                    "uploaded_on": "July 07, 2026",
                    "approved": false
                }
            ]
        }
        ```
        """
        user = get_object_or_404(User.objects.select_related("phlebotomist_profile", "client_profile").prefetch_related("phlebotomist_profile__documents", "client_profile__documents"), id=user_id)

        # Helper: format file size into a human-readable string
        def format_file_size(file_field):
            try:
                size_bytes = file_field.size
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
            except (FileNotFoundError, OSError):
                return None

        # Safely resolve the profile — catch RelatedObjectDoesNotExist in case
        # a user row exists without a completed profile (e.g. interrupted registration).
        try:
            phlebotomist_profile = user.phlebotomist_profile
        except Exception:
            phlebotomist_profile = None

        try:
            client_profile = user.client_profile
        except Exception:
            client_profile = None

        is_phlebotomist = phlebotomist_profile is not None
        profile = phlebotomist_profile if is_phlebotomist else client_profile

        if profile is None:
            return Response({"detail": "User profile not found."}, status=404)

        docs = profile.documents.all()

        return Response(
            {
                "id": user.id,
                "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                "name": user.full_name,
                "email": user.email,
                "phone_number": user.phone_number,
                "gender": user.gender,
                "dob": user.dob,
                "role": user.role,
                "registration_date": user.created_at.strftime("%Y-%m-%d"),
                "experience": phlebotomist_profile.years_of_experience if is_phlebotomist else None,
                "address": phlebotomist_profile.service_area if is_phlebotomist else f"{client_profile.business_address_street}, {client_profile.business_address_city}, {client_profile.business_address_state}, {client_profile.business_address_zip}",
                "is_approved": phlebotomist_profile.approved if is_phlebotomist else client_profile.is_approved,
                "uploaded_documents": [
                    {
                        "id": doc.id,
                        "document_name": doc.document_name,
                        "file_name": doc.document_file.name.split("/")[-1],
                        "file_size": format_file_size(doc.document_file),
                        "document_file": request.build_absolute_uri(doc.document_file.url),
                        "uploaded_on": doc.created_at.strftime("%B %d, %Y"),
                        "approved": doc.approved,
                    }
                    for doc in docs
                ],
            }
        )

class UserApprovalAPIView(NewAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.BooleanSerializer
    http_method_names = ['patch', 'delete']

    @swagger_auto_schema(tags=["Dashboard Endpoints"])
    def patch(self, request, user_id):
        """
        **Approve or Reject User - Admin Only**\n
        Approve or reject a specific user (client or phlebotomist) for registration.\n
        
        **Parameters:**
        - **user_id**: The ID of the user to approve or reject.
        
        **Request Body:**
        - **approve**: Boolean value indicating whether to approve (true) or reject (false) the user.
        
        **Response:**
        - **detail**: Message indicating the result of the operation.
        
        **Example Request Body**:
        ```Json
        {
            "approve": true
        }
        ```
        
        **Example Response**:
        ```Json
        {
            "detail": "User approved successfully."
        }
        ```
        """
        user = get_object_or_404(User.objects.select_related("phlebotomist_profile", "client_profile").filter(role__in=["phlebotomist", "client"]), id=user_id)

        is_phlebotomist = hasattr(user, 'phlebotomist_profile')
        profile = user.phlebotomist_profile if is_phlebotomist else user.client_profile

        if profile is None:
            return Response({"detail": "User profile not found."}, status=404)

        approve = request.data.get("approve")
        if approve is None:
            return Response({"detail": "Missing 'approve' field in request body."}, status=400)

        profile.approved = approve if is_phlebotomist else None
        profile.is_approved = approve if not is_phlebotomist else None
        profile.save()

        action = "approved" if approve else "rejected"
        return Response({"detail": f"User {action} successfully."}, status=200)


