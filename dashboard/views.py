from phlebotomy_staffing.base import AutoPaginatedResponse, NewAPIView
from rest_framework.response import Response
from rest_framework import status
from dashboard import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from authentication.serializers import EmptySerializer
from authentication.models import Client, ClientDocument, Phlebotomist, Phlebotomist_document
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.views import APIView
from jobs.models import Job, JobAssignment

User = get_user_model()

# Dashboard Home Page Endpoints
class DashboardHomeView(NewAPIView):
    serializer_class = serializers.DashboardHomeSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    @swagger_auto_schema(tags=['Dashboard - Dashboard Page'])
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
    
    @swagger_auto_schema(tags=['Dashboard - Dashboard Page'])
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
    
    @swagger_auto_schema(tags=['Dashboard - Dashboard Page'])
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

    @swagger_auto_schema(tags=["Dashboard - Dashboard Page"])
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

class UserDocumentApprovalAPIView(NewAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = serializers.BooleanSerializer
    http_method_names = ['patch']

    @swagger_auto_schema(tags=["Dashboard - Dashboard Page"])
    def patch(self, request, user_id, document_id):
        """
        **Approve or Reject User Document - Admin Only**\n
        Approve or reject a specific user document (client or phlebotomist) for verification.\n
        
        **Parameters:**
        - **document_id**: The ID of the document to approve or reject.
        
        **Request Body:**
        - **approve**: Boolean value indicating whether to approve (true) or reject (false) the document.
        
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
            "detail": "Document approved successfully."
        }
        ```
        """
        user = get_object_or_404(User, id=user_id)
        if user.role not in ["phlebotomist", "client"]:
            return Response({"detail": "User is not a phlebotomist or client."}, status=400)
        if user.role == "phlebotomist":
            document = get_object_or_404(Phlebotomist_document, id=document_id, phlebotomist__user=user)
        elif user.role == "client":
            document = get_object_or_404(ClientDocument, id=document_id, client__client=user)
        document.approved = request.data.get("approve")
        document.save()
        action = "approved" if document.approved else "rejected"
        return Response({"detail": f"Document {action} successfully."}, status=200)

# Documents to verify
class PendingDocumentsAPIView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    @swagger_auto_schema(tags=['Dashboard - Dashboard Page'])
    def get(self, request):
        """
        **Get Pending Documents for Verification - Admin Only**\n
        Retrieve a list of pending documents for verification for both clients and phlebotomists.\n
        
        **Query Parameters:**
        - **page**: Page number (default: 1).
        - **page_size**: Number of items per page (default: 10).
        - **search**: Search query for user name or document name.
        - **ordering**: Field to sort by (default: 'id').
        - **filter**: Filter documents based on approval status.
        
        **Response:**
        - **success**: Boolean indicating whether the request was successful.
        - **pagination**: Pagination information.
        - **results**: List of pending documents.
        
        **Example Response:**
        ```
        {
        "success": true,
        "pagination": {
            "count": 8,
            "total_pages": 1,
            "current_page": 1,
            "next": null,
            "previous": null
        },
        "results": [
                {
                    "id": 1,
                    "user_id": 2,
                    "user_name": "Md. Fahad Monshi",
                    "user_role": "Phlebotomist",
                    "document_name": "Phlebotomy Certification",
                    "document_file": "http://10.10.13.43:8001/media/phlebotomist_documents/Md_Fahad_Monshi_CV.pdf",
                    "uploaded_on": "Jul 07, 2026",
                    "uploaded_ago": "4 hours ago",
                    "approved": false
                },
                {
                    "id": 3,
                    "user_id": 6,
                    "user_name": "Abrar Ahmed",
                    "user_role": "Phlebotomist",
                    "document_name": "license",
                    "document_file": "http://10.10.13.43:8001/media/phlebotomist_documents/Md_Fahad_Monshi_CV_d3YLHkF.pdf",
                    "uploaded_on": "Jul 07, 2026",
                    "uploaded_ago": "3 hours ago",
                    "approved": null
                }
            ]
        }
        ```
        """
        from django.utils.timezone import now
        from datetime import timedelta

        # Helper: calculate relative time
        def get_relative_time(upload_datetime):
            delta = now() - upload_datetime
            if delta < timedelta(minutes=1):
                return "just now"
            elif delta < timedelta(hours=1):
                minutes = int(delta.total_seconds() / 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif delta < timedelta(days=1):
                hours = int(delta.total_seconds() / 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif delta < timedelta(days=30):
                days = delta.days
                return f"{days} day{'s' if days != 1 else ''} ago"
            elif delta < timedelta(days=365):
                months = int(delta.days / 30)
                return f"{months} month{'s' if months != 1 else ''} ago"
            else:
                years = int(delta.days / 365)
                return f"{years} year{'s' if years != 1 else ''} ago"

        phlebotomist_documents = Phlebotomist_document.objects.filter(Q(approved=False) | Q(approved=None)).select_related('phlebotomist__user')
        client_documents = ClientDocument.objects.filter(Q(approved=False) | Q(approved=None)).select_related('client__client')
        documents = []
        for doc in phlebotomist_documents:
            documents.append({
                "id": doc.id,
                "user_id": doc.phlebotomist.user.id,
                "user_name": doc.phlebotomist.user.full_name,
                "user_role": "Phlebotomist",
                "document_name": doc.document_name,
                "document_file": request.build_absolute_uri(doc.document_file.url),
                "uploaded_on": doc.created_at.strftime("%b %d, %Y"),
                "uploaded_ago": get_relative_time(doc.created_at),
                "approved": doc.approved
            })
        for doc in client_documents:
            documents.append({
                "id": doc.id,
                "user_id": doc.client.client.id,
                "user_name": doc.client.client.full_name,
                "user_role": "Client",
                "document_name": doc.document_name,
                "document_file": request.build_absolute_uri(doc.document_file.url),
                "uploaded_on": doc.created_at.strftime("%b %d, %Y"),
                "uploaded_ago": get_relative_time(doc.created_at),
                "approved": doc.approved
            })
        return AutoPaginatedResponse(documents, request=request)

class SuspendUserAccount(APIView):
    permission_classes = [IsAdminUser]
    http_method_names = ['patch']
    
    @swagger_auto_schema(tags=["Dashboard - Dashboard Page"])
    def patch(self, request, user_id):
        """
        **Suspend User Account - Admin Only**\n
        Suspend or unsuspend a specific user account - Admin Only\n
        
        **Parameters:**
        - **user_id**: The ID of the user to suspend or unsuspend.
        
        **Response:**
        - **detail**: Message indicating the result of the operation.
        
        **Example Response:**
        ```Json
        {
            "detail": "User account suspended successfully."
        }
        ```
        """
        user = get_object_or_404(User, id=user_id)
        user.suspended = True if user.suspended == False else False
        user.save()
        return Response({"detail": f"User account {'suspended' if user.suspended else 'unsuspended'} successfully."}, status=status.HTTP_200_OK)


# Dashboard User Managements Views
class UserListAPIView(APIView):
    permission_classes = [IsAdminUser]
    http_method_names = ['get']
    
    @swagger_auto_schema(tags=["Dashboard - User Management Page"])
    def get(self, request):
        """
        **Get User List - Admin Only**\n
        Get a list of all users registered on the platform.\n
        
        **Response:**
        - **users**: A list of user objects.
        
        **Example Response:**
        ```Json
        {
            "result": [
                {
                    "id": 1,
                    "profile_picture": "http://localhost:8001/media/profile_pictures/fahad_Fc2dmEM.jpg",
                    "full_name": "John Doe",
                    "role": "phlebotomist",
                    "status": "active",
                    "joined_at": "Jan 12, 2024"
                },
                {
                    "id": 2,
                    "profile_picture": "http://localhost:8001/media/profile_pictures/fahad_Fc2dmEM.jpg",
                    "full_name": "Jane Doe",
                    "role": "client",
                    "status": "active",
                    "joined_at": "Jan 12, 2024"
                }
            ]
        }
        ```
        """
        users = User.objects.select_related('phlebotomist_profile', 'client_profile').all()

        def get_user_status(user):
            if user.suspended:
                return "suspended"
            if not user.is_active:
                return "inactive"
            # Resolve profile approval field (phlebotomist uses 'approved', client uses 'is_approved')
            try:
                approval = user.phlebotomist_profile.approved
            except Exception:
                try:
                    approval = user.client_profile.is_approved
                except Exception:
                    approval = None
            if approval is None:
                return "pending"
            if approval is False:
                return "rejected"
            return "active"

        data = []
        for user in users:
            data.append({
                "id": user.id,
                "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                "full_name": user.full_name,
                "role": user.role,
                "status": get_user_status(user),
                "joined_at": user.created_at.strftime("%b %d, %Y")
            })
        return AutoPaginatedResponse(data, request=request)

class UserManagementDetailView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['Dashboard - User Management Page'])
    def get(self, request, user_id):
        """
        **Get Full User Details - Admin Only**\n
        Returns a comprehensive profile for a single user including personal info,
        professional info (phlebotomist only), activity summary, and document verification.\n

        ### Parameters:
        - **user_id**: The ID of the user to retrieve.

        ### Response Sections:
        - **header**: Name, role, status, member since, overall rating.
        - **personal_information**: Email, phone, DOB, address, license number (phlebotomist).
        - **professional_information**: Years of experience, skills (phlebotomist only).
        - **activity_summary**: Jobs completed, success rate, last active.
        - **document_verification**: List of uploaded documents with approval status.

        ### Example Response:
        ```json
        {
            "header": {
                "user_id": 1,
                "profile_picture": "http://localhost:8001/media/profile_pictures/kabita.jpg",
                "full_name": "FA Kabita",
                "role": "Phlebotomist",
                "status": "active",
                "member_since": "March 2025",
                "overall_rating": 4.8
            },
            "personal_information": {
                "email": "kabita@example.com",
                "phone_number": "(555) 123-4567",
                "dob": "March 15, 1990",
                "address": "1234 XYZ, Dhaka-1216",
                "license_number": "PHL-2023-789456"
            },
            "professional_information": {
                "years_of_experience": 3.5,
                "skills": ["Blood Collection", "IV Insertion"]
            },
            "activity_summary": {
                "jobs_completed": 247,
                "success_rate": 4.8,
                "last_active": "2 hours ago"
            },
            "document_verification": [
                {
                    "id": 1,
                    "document_name": "Phlebotomy License",
                    "uploaded_on": "Jan 15, 2024",
                    "document_file": "http://localhost:8001/media/phlebotomist_documents/license.pdf",
                    "approved": true
                }
            ]
        }
        ```

        ### Responses:
        - **200 OK**: Full user profile returned.
        - **404 Not Found**: User does not exist.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        from jobs.models import JobAssignment

        user = get_object_or_404(
            User.objects.select_related('phlebotomist_profile', 'client_profile')
                        .prefetch_related(
                            'phlebotomist_profile__documents',
                            'phlebotomist_profile__skills',
                            'client_profile__documents',
                        ),
            id=user_id
        )

        # ── Resolve profile ──────────────────────────────────────────────────
        try:
            profile = user.phlebotomist_profile
            is_phlebotomist = True
        except Exception:
            try:
                profile = user.client_profile
                is_phlebotomist = False
            except Exception:
                profile = None
                is_phlebotomist = False

        # ── Status ───────────────────────────────────────────────────────────
        def get_status(u, p, is_phleb):
            if u.suspended:
                return "suspended"
            if not u.is_active:
                return "inactive"
            if p is None:
                return "pending"
            approval = p.approved if is_phleb else getattr(p, 'is_approved', None)
            if approval is None:
                return "pending"
            if approval is False:
                return "rejected"
            return "active"

        # ── Relative time helper ─────────────────────────────────────────────
        def relative_time(dt):
            if dt is None:
                return "Never"
            delta = now() - dt
            if delta < timedelta(minutes=1):
                return "just now"
            elif delta < timedelta(hours=1):
                m = int(delta.total_seconds() / 60)
                return f"{m} minute{'s' if m != 1 else ''} ago"
            elif delta < timedelta(days=1):
                h = int(delta.total_seconds() / 3600)
                return f"{h} hour{'s' if h != 1 else ''} ago"
            elif delta < timedelta(days=30):
                return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
            elif delta < timedelta(days=365):
                mo = int(delta.days / 30)
                return f"{mo} month{'s' if mo != 1 else ''} ago"
            else:
                yr = int(delta.days / 365)
                return f"{yr} year{'s' if yr != 1 else ''} ago"

        # ── Activity summary ─────────────────────────────────────────────────
        if is_phlebotomist:
            completed_assignments = JobAssignment.objects.filter(
                phlebotomist=user, status='completed'
            )
            jobs_completed = completed_assignments.count()
            total_applications = user.job_applications.count()
            success_rate = round((jobs_completed / total_applications) * 5, 1) if total_applications > 0 else 0.0
            last_assignment = completed_assignments.order_by('-end_time').first()
            last_active = relative_time(last_assignment.end_time if last_assignment else None)
        else:
            completed_jobs = user.jobs.filter(status='completed').count() if profile else 0
            jobs_completed = completed_jobs
            success_rate = None
            last_active = relative_time(user.updated_at)

        # ── Personal information ─────────────────────────────────────────────
        personal_info = {
            "email": user.email,
            "phone_number": user.phone_number,
            "dob": user.dob.strftime("%B %d, %Y") if user.dob else None,
        }
        if is_phlebotomist and profile:
            personal_info["address"] = profile.address or profile.service_area
            personal_info["license_number"] = profile.license_number
        elif profile:
            personal_info["address"] = (
                f"{profile.business_address_street}, "
                f"{profile.business_address_city}-{profile.business_address_zip}"
            )

        # ── Professional information (phlebotomist only) ──────────────────────
        professional_info = None
        if is_phlebotomist and profile:
            professional_info = {
                "years_of_experience": profile.years_of_experience,
                "skills": [s.skill_name for s in profile.skills.all()],
            }

        # ── Document verification ─────────────────────────────────────────────
        if profile:
            docs = profile.documents.all()
        else:
            docs = []

        documents = [
            {
                "id": doc.id,
                "document_name": doc.document_name,
                "uploaded_on": doc.created_at.strftime("%b %d, %Y"),
                "document_file": request.build_absolute_uri(doc.document_file.url),
                "approved": doc.approved,
            }
            for doc in docs
        ]

        # ── Build response ────────────────────────────────────────────────────
        return Response({
            "header": {
                "user_id": user.id,
                "profile_picture": request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                "full_name": user.full_name,
                "role": user.role.capitalize(),
                "status": get_status(user, profile, is_phlebotomist),
                "member_since": user.created_at.strftime("%B %Y"),
                "overall_rating": success_rate,
            },
            "personal_information": personal_info,
            "professional_information": professional_info,
            "activity_summary": {
                "jobs_completed": jobs_completed,
                "success_rate": success_rate,
                "last_active": last_active,
            },
            "document_verification": documents,
        }, status=status.HTTP_200_OK)

class UserManagementEditView(NewAPIView):
    serializer_class = serializers.PhlebotomistProfileEditSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['patch']

    @swagger_auto_schema(
        tags=['Dashboard - User Management Page'],
        request_body=serializers.PhlebotomistProfileEditSerializer
    )
    def patch(self, request, user_id):
        """
        **Edit User Profile - Admin Only**\n
        Partially update any user's profile (both phlebotomist and client).
        Only include the fields you want to change — omitted fields remain untouched.\n

        Supports `multipart/form-data` for file uploads (`profile_picture`, `signature`)
        and `application/json` for all other fields.\n

        ### Editable User Fields:
        - `full_name` (string)
        - `email` (string)
        - `phone_number` (string)
        - `gender` (string): `male`, `female`
        - `dob` (date): `YYYY-MM-DD`
        - `profile_picture` (file): image upload

        ### Editable Phlebotomist Profile Fields:
        - `license_number` (string)
        - `license_expiry_date` (date): `YYYY-MM-DD`
        - `years_of_experience` (integer)
        - `specialty` (string): `general_phlebotomy`, `iv_insertion_or_therapy`, `oncology_or_chemotherapy`, `medical_nurse`
        - `work_preference` (string): `part_time`, `full_time`
        - `service_area` (string)
        - `address` (string)
        - `skills` (list of strings): replaces all existing skills e.g. `["venipuncture", "iv_insertion"]`
        - `availabilities` (list): replaces all existing slots. Each item: `{day, date, start_time, end_time, is_available}`

        ### Editable Client Profile Fields:
        - `business_name` (string)
        - `business_type` (string): `healthcare`, `individual`
        - `business_address_street` (string)
        - `business_address_city` (string)
        - `business_address_state` (string)
        - `business_address_zip` (string)
        - `contact_person_name` (string)
        - `business_phone` (string)
        - `business_license_number` (string)
        - `business_description` (string)
        - `hourly_pay_rate` (decimal)
        - `preferred_job_type` (string): `in_clinic_phlebotomy`, `mobile_blood_draw`, `laboratory_testing`
        - `work_preference` (string): `part_time`, `full_time`
        - `no_of_employees` (integer)
        - `signature` (file): image upload
        - `availabilities` (list): replaces all existing slots. Each item: `{day, date, start_time, end_time, is_available}`

        ### Example Request (phlebotomist):
        ```json
        {
            "full_name": "Jane Doe",
            "phone_number": "1234567890",
            "years_of_experience": 5,
            "service_area": "Brooklyn",
            "skills": ["venipuncture", "iv_insertion"]
        }
        ```

        ### Example Request (client):
        ```json
        {
            "business_name": "New Clinic Name",
            "business_address_city": "Los Angeles",
            "hourly_pay_rate": "35.00"
        }
        ```

        ### Example Success Response:
        ```json
        {
            "message": "Profile updated successfully."
        }
        ```
        
        ### Exmaple Request Full (Client):
        ```json
        {
            "full_name": "John Smith",
            "email": "john@example.com",
            "phone_number": "9876543210",
            "gender": "male",
            "dob": "1985-06-15",
            "business_name": "Smith Healthcare LLC",
            "business_type": "healthcare",
            "business_address_street": "123 Main Street",
            "business_address_city": "New York",
            "business_address_state": "NY",
            "business_address_zip": "10001",
            "contact_person_name": "John Smith",
            "business_phone": "2125550100",
            "business_license_number": "BL-987654",
            "business_description": "A private healthcare clinic offering routine blood draws.",
            "hourly_pay_rate": "35.00",
            "preferred_job_type": "in_clinic_phlebotomy",
            "work_preference": "full_time",
            "no_of_employees": 12,
            "availabilities": [
                {
                    "day": "Monday",
                    "date": "2025-09-01",
                    "start_time": "08:00",
                    "end_time": "16:00",
                    "is_available": true
                },
                {
                    "day": "Wednesday",
                    "date": "2025-09-03",
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "is_available": true
                }
            ]
        }
        ```
        
        ### Example Request Full (Phlebotomist):
        ```json
        {
            "full_name": "FA Kabita",
            "email": "kabita@example.com",
            "phone_number": "1234567890",
            "gender": "female",
            "dob": "1990-03-15",
            "license_number": "PHL-2023-789456",
            "license_expiry_date": "2027-12-31",
            "years_of_experience": 4,
            "specialty": "general_phlebotomy",
            "work_preference": "full_time",
            "service_area": "Brooklyn, New York",
            "address": "1234 XYZ, Dhaka-1216",
            "skills": [
                "venipuncture",
                "capillary_puncture",
                "iv_insertion_or_therapy",
                "pediatric_draw"
            ],
            "availabilities": [
                {
                    "day": "Monday",
                    "date": "2025-09-01",
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "is_available": true
                },
                {
                    "day": "Tuesday",
                    "date": "2025-09-02",
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "is_available": true
                },
                {
                    "day": "Thursday",
                    "date": "2025-09-04",
                    "start_time": "10:00",
                    "end_time": "15:00",
                    "is_available": false
                }
            ]
        }
        ```

        ### Responses:
        - **200 OK**: Profile updated.
        - **400 Bad Request**: Validation error.
        - **404 Not Found**: User does not exist.
        """
        import json
        import datetime
        from decimal import Decimal, InvalidOperation
        from authentication.models import (
            PhlebotomistAvailability, Phlebotomist_skill,
            ClientWeeklySchedule
        )

        user = get_object_or_404(
            User.objects.select_related('phlebotomist_profile', 'client_profile'),
            id=user_id
        )

        data = request.data
        errors = {}

        # ── Resolve profile ───────────────────────────────────────────────────
        try:
            profile = user.phlebotomist_profile
            is_phlebotomist = True
        except Exception:
            try:
                profile = user.client_profile
                is_phlebotomist = False
            except Exception:
                profile = None
                is_phlebotomist = False

        # ── Validate & apply User fields ──────────────────────────────────────
        user_dirty = False

        if 'full_name' in data:
            val = data['full_name'].strip()
            if not val:
                errors['full_name'] = ["This field may not be blank."]
            else:
                user.full_name = val
                user_dirty = True

        if 'email' in data:
            val = data['email'].strip().lower()
            if not val:
                errors['email'] = ["This field may not be blank."]
            elif User.objects.filter(email__iexact=val).exclude(pk=user.pk).exists():
                errors['email'] = ["A user with this email already exists."]
            else:
                user.email = val
                user_dirty = True

        if 'phone_number' in data:
            val = data['phone_number'].strip()
            if not val:
                errors['phone_number'] = ["This field may not be blank."]
            else:
                user.phone_number = val
                user_dirty = True

        if 'gender' in data:
            valid = [c[0] for c in User.GENDER_CHOICES]
            if data['gender'] not in valid:
                errors['gender'] = [f"Invalid choice. Valid options: {valid}"]
            else:
                user.gender = data['gender']
                user_dirty = True

        if 'dob' in data:
            try:
                user.dob = datetime.date.fromisoformat(data['dob'])
                user_dirty = True
            except ValueError:
                errors['dob'] = ["Invalid date format. Use YYYY-MM-DD."]

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
            user_dirty = True

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        if user_dirty:
            user.save()

        # ── Validate & apply profile fields ───────────────────────────────────
        if profile is None:
            return Response(
                {"message": "Profile updated successfully." if user_dirty else "No changes provided."},
                status=status.HTTP_200_OK
            )

        profile_dirty = False

        if is_phlebotomist:
            # -- Phlebotomist direct fields
            str_fields = ['license_number', 'service_area', 'address']
            for field in str_fields:
                if field in data:
                    val = data[field].strip() if data[field] else None
                    setattr(profile, field, val)
                    profile_dirty = True

            if 'license_expiry_date' in data:
                try:
                    profile.license_expiry_date = datetime.date.fromisoformat(data['license_expiry_date'])
                    profile_dirty = True
                except ValueError:
                    errors['license_expiry_date'] = ["Invalid date format. Use YYYY-MM-DD."]

            if 'years_of_experience' in data:
                try:
                    val = int(data['years_of_experience'])
                    if val < 0:
                        errors['years_of_experience'] = ["Must be a non-negative integer."]
                    else:
                        profile.years_of_experience = val
                        profile_dirty = True
                except (ValueError, TypeError):
                    errors['years_of_experience'] = ["Enter a valid integer."]

            if 'specialty' in data:
                valid = [c[0] for c in profile.SPECIALTY_CHOICES]
                if data['specialty'] not in valid:
                    errors['specialty'] = [f"Invalid choice. Valid options: {valid}"]
                else:
                    profile.specialty = data['specialty']
                    profile_dirty = True

            if 'work_preference' in data:
                valid = [c[0] for c in profile.WORK_PREFERENCE_CHOICES]
                if data['work_preference'] not in valid:
                    errors['work_preference'] = [f"Invalid choice. Valid options: {valid}"]
                else:
                    profile.work_preference = data['work_preference']
                    profile_dirty = True

            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)

            from django.db import transaction
            with transaction.atomic():
                if profile_dirty:
                    profile.save()

                # -- Skills: full replace
                if 'skills' in data:
                    raw = data['skills']
                    if isinstance(raw, str):
                        try:
                            raw = json.loads(raw)
                        except json.JSONDecodeError:
                            return Response({'skills': ["Invalid JSON format."]}, status=status.HTTP_400_BAD_REQUEST)
                    if not isinstance(raw, list):
                        return Response({'skills': ["Must be a list of skill names."]}, status=status.HTTP_400_BAD_REQUEST)
                    profile.skills.all().delete()
                    for skill_name in raw:
                        if skill_name:
                            Phlebotomist_skill.objects.get_or_create(phlebotomist=profile, skill_name=skill_name.strip())

                # -- Availabilities: full replace
                if 'availabilities' in data:
                    raw = data['availabilities']
                    if isinstance(raw, str):
                        try:
                            raw = json.loads(raw)
                        except json.JSONDecodeError:
                            return Response({'availabilities': ["Invalid JSON format."]}, status=status.HTTP_400_BAD_REQUEST)
                    if not isinstance(raw, list):
                        return Response({'availabilities': ["Must be a list."]}, status=status.HTTP_400_BAD_REQUEST)
                    profile.availabilities.all().delete()
                    for slot in raw:
                        try:
                            PhlebotomistAvailability.objects.create(
                                phlebotomist=profile,
                                day=slot['day'],
                                date=datetime.date.fromisoformat(slot['date']),
                                start_time=datetime.time.fromisoformat(slot['start_time']),
                                end_time=datetime.time.fromisoformat(slot['end_time']),
                                is_available=slot.get('is_available', True),
                            )
                        except (KeyError, ValueError) as e:
                            raise ValueError(f"Invalid slot data: {e}")

        else:
            # -- Validate choices FIRST before touching the model
            if 'business_type' in data:
                valid = [c[0] for c in profile.BUSINESS_TYPE_CHOICES]
                if data['business_type'] not in valid:
                    errors['business_type'] = [f"Invalid choice. Valid options: {valid}"]

            if 'preferred_job_type' in data:
                valid = [c[0] for c in profile.JOB_PREFERENCE_CHOICES]
                if data['preferred_job_type'] not in valid:
                    errors['preferred_job_type'] = [f"Invalid choice. Valid options: {valid}"]

            if 'work_preference' in data:
                valid = [c[0] for c in profile.WORK_PREFERENCE_CHOICES]
                if data['work_preference'] not in valid:
                    errors['work_preference'] = [f"Invalid choice. Valid options: {valid}"]

            if 'no_of_employees' in data:
                try:
                    val = int(data['no_of_employees'])
                    if val < 0:
                        errors['no_of_employees'] = ["Must be a non-negative integer."]
                except (ValueError, TypeError):
                    errors['no_of_employees'] = ["Enter a valid integer."]

            if 'hourly_pay_rate' in data:
                try:
                    val = Decimal(str(data['hourly_pay_rate']))
                    if val < 0:
                        errors['hourly_pay_rate'] = ["Must be a positive value."]
                except InvalidOperation:
                    errors['hourly_pay_rate'] = ["Enter a valid decimal number."]

            if 'availabilities' in data:
                raw = data['availabilities']
                if isinstance(raw, str):
                    try:
                        raw = json.loads(raw)
                    except json.JSONDecodeError:
                        errors['availabilities'] = ["Invalid JSON format."]
                if not isinstance(raw, list) and 'availabilities' not in errors:
                    errors['availabilities'] = ["Must be a list."]

            if errors:
                return Response(errors, status=status.HTTP_400_BAD_REQUEST)

            # -- All validation passed — apply changes atomically
            from django.db import transaction
            with transaction.atomic():
                # String / choice fields
                str_fields = [
                    'business_name', 'business_type', 'business_address_street',
                    'business_address_city', 'business_address_state', 'business_address_zip',
                    'contact_person_name', 'business_phone', 'business_license_number',
                    'business_description', 'preferred_job_type', 'work_preference',
                ]
                for field in str_fields:
                    if field in data:
                        setattr(profile, field, data[field].strip() if data[field] else '')
                        profile_dirty = True

                if 'no_of_employees' in data:
                    profile.no_of_employees = int(data['no_of_employees'])
                    profile_dirty = True

                if 'hourly_pay_rate' in data:
                    profile.hourly_pay_rate = Decimal(str(data['hourly_pay_rate']))
                    profile_dirty = True

                if 'signature' in request.FILES:
                    profile.signature = request.FILES['signature']
                    profile_dirty = True

                if profile_dirty:
                    profile.save()

                # -- Availabilities: full replace
                if 'availabilities' in data:
                    raw = data['availabilities']
                    if isinstance(raw, str):
                        raw = json.loads(raw)
                    profile.availabilities.all().delete()
                    for slot in raw:
                        try:
                            ClientWeeklySchedule.objects.create(
                                client=profile,
                                day=slot['day'],
                                date=datetime.date.fromisoformat(slot['date']),
                                start_time=datetime.time.fromisoformat(slot['start_time']),
                                end_time=datetime.time.fromisoformat(slot['end_time']),
                                is_available=slot.get('is_available', True),
                            )
                        except (KeyError, ValueError) as e:
                            raise ValueError(f"Invalid slot data: {e}")

        return Response({"message": "Profile updated successfully."}, status=status.HTTP_200_OK)


# Dashboard Job Management Views
class JobManagementListView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['Dashboard - Job Management Page'])
    def get(self, request):
        """
        **Get All Jobs - Admin Only**\n
        Returns a paginated list of all job postings with support for search, status, and date filters.
        Matches the Job Management page on the dashboard.\n

        ### Query Parameters:
        - `search` (string): Filter by job title or job ID (case-insensitive).
        - `status` (string): Filter by job status. Choices: `draft`, `pending_approval`, `approved`, `open`, `in_progress`, `completed`, `cancelled`.
        - `date` (string): Filter by shift date in `YYYY-MM-DD` format.

        ### Example Response:
        ```json
        {
            "success": true,
            "pagination": {
                "count": 2,
                "total_pages": 1,
                "current_page": 1,
                "next": null,
                "previous": null
            },
            "results": [
                {
                    "id": "JB-26-000002",
                    "title": "Jr. Backend Dev at JVAI",
                    "client_business_name": "Join Venture AI",
                    "city": "Dhaka",
                    "pay_rate": "10.00",
                    "pay_type": "flat_rate",
                    "status": "pending_approval",
                    "posted_ago": "6 hours ago",
                    "shift_date": "2026-07-09"
                },
                {
                    "id": "JB-26-000001",
                    "title": "Trainee Backend Dev at JVAI",
                    "client_business_name": "Join Venture AI",
                    "city": "Dhaka",
                    "pay_rate": "10.00",
                    "pay_type": "hourly",
                    "status": "pending_approval",
                    "posted_ago": "6 hours ago",
                    "shift_date": "2026-07-08"
                }
            ]
        }
        ```

        ### Responses:
        - **200 OK**: Paginated list of jobs.
        - **400 Bad Request**: Invalid date format.
        """
        from django.utils.timezone import now
        from datetime import timedelta
        from jobs.models import Job

        # ── Filters ───────────────────────────────────────────────────────────
        search     = request.query_params.get('search', '').strip()
        status_filter = request.query_params.get('status', '').strip()
        date_filter   = request.query_params.get('date', '').strip()

        jobs = Job.objects.select_related('client__client_profile').order_by('-created_at')

        if search:
            jobs = jobs.filter(
                Q(title__icontains=search) | Q(id__icontains=search)
            )

        if status_filter:
            jobs = jobs.filter(status=status_filter)

        if date_filter:
            import datetime
            try:
                parsed_date = datetime.date.fromisoformat(date_filter)
                jobs = jobs.filter(shift_date=parsed_date)
            except ValueError:
                return Response(
                    {"date": ["Invalid date format. Use YYYY-MM-DD."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ── Relative time helper ──────────────────────────────────────────────
        def posted_ago(created_at):
            delta = now() - created_at
            if delta < timedelta(minutes=1):
                return "just now"
            elif delta < timedelta(hours=1):
                m = int(delta.total_seconds() / 60)
                return f"{m} minute{'s' if m != 1 else ''} ago"
            elif delta < timedelta(days=1):
                h = int(delta.total_seconds() / 3600)
                return f"{h} hour{'s' if h != 1 else ''} ago"
            elif delta < timedelta(days=30):
                return f"{delta.days} day{'s' if delta.days != 1 else ''} ago"
            elif delta < timedelta(days=365):
                mo = int(delta.days / 30)
                return f"{mo} month{'s' if mo != 1 else ''} ago"
            else:
                yr = int(delta.days / 365)
                return f"{yr} year{'s' if yr != 1 else ''} ago"

        def get_business_name(job):
            try:
                return job.client.client_profile.business_name
            except Exception:
                return job.client.full_name

        data = [
            {
                "id":                   job.id,
                "title":                job.title,
                "client_business_name": get_business_name(job),
                "city":                 job.city or job.location,
                "pay_rate":             str(job.pay_rate),
                "pay_type":             job.pay_type,
                "status":               job.status,
                "posted_ago":           posted_ago(job.created_at),
                "shift_date":           str(job.shift_date),
            }
            for job in jobs
        ]

        response = AutoPaginatedResponse(data, request=request)
        return response

class JobManagementDetailView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['Dashboard - Job Management Page'])
    def get(self, request, job_id):
        """
        **Get Job Details - Admin Only**\n
        Returns full details of a single job posting as shown on the Job Detail page.\n

        ### Parameters:
        - **job_id**: The formatted job ID (e.g. `JB-25-000001`).

        ### Response Sections:
        - **header**: Job title, job ID, posted date, job type, pay rate, shift start date.
        - **job_description**: Full description text.
        - **payment_and_timeline**: Pay rate, pay type, shift date, shift duration, work schedule.
        - **client_information**: Business name, business type, no. of employees, member since.
        - **location_and_work_type**: Full location, shift time window.
        - **status**: Current job approval status.

        ### Example Response:
        ```json
        {
            "header": {
                "title": "Blood Draw Station",
                "job_id": "JB-25-000001",
                "posted_on": "July 30, 2025",
                "job_type": "full_day",
                "pay_rate": "30.00",
                "pay_type": "hourly",
                "shift_date": "August 1, 2025"
            },
            "job_description": "A phlebotomist is responsible for...",
            "payment_and_timeline": {
                "pay_rate": "30.00",
                "pay_type": "hourly",
                "shift_date": "2025-08-15",
                "shift_duration": "8 hrs",
                "work_schedule": "10:00 AM to 12:00 PM"
            },
            "client_information": {
                "client_id": 4,
                "business_name": "Community Health Center",
                "business_type": "healthcare",
                "no_of_employees": 250,
                "member_since": "2020"
            },
            "location_and_work_type": {
                "location": "XYZ XYZ XYZ",
                "work_schedule": "10:00 AM to 12:00 PM"
            },
            "status": "pending_approval"
        }
        ```

        ### Responses:
        - **200 OK**: Full job detail returned.
        - **404 Not Found**: Job does not exist.
        """
        from jobs.models import Job

        job = get_object_or_404(
            Job.objects.select_related('client__client_profile'),
            id=job_id
        )

        # ── Client info ───────────────────────────────────────────────────────
        try:
            client_profile  = job.client.client_profile
            business_name   = client_profile.business_name
            business_type   = client_profile.business_type
            no_of_employees = client_profile.no_of_employees
            member_since    = job.client.created_at.strftime("%Y")
        except Exception:
            business_name   = job.client.full_name
            business_type   = None
            no_of_employees = None
            member_since    = job.client.created_at.strftime("%Y")

        # ── Work schedule string ──────────────────────────────────────────────
        work_schedule = (
            f"{job.shift_start.strftime('%I:%M %p').lstrip('0')} to "
            f"{job.shift_end.strftime('%I:%M %p').lstrip('0')}"
        )

        # ── Shift duration display ────────────────────────────────────────────
        shift_duration_display = (
            f"{job.shift_duration} hr{'s' if job.shift_duration != 1 else ''}"
            if job.shift_duration
            else "N/A"
        )

        return Response(
            {
                "header": {
                    "title":      job.title,
                    "job_id":     f"#{job.id}",
                    "posted_on":  job.created_at.strftime("%B %d, %Y"),
                    "job_type":   job.job_type,
                    "pay_rate":   str(job.pay_rate),
                    "pay_type":   job.pay_type,
                    "shift_date": job.shift_date.strftime("%B %d, %Y"),
                },
                "job_description": job.description,
                "payment_and_timeline": {
                    "pay_rate":        str(job.pay_rate),
                    "pay_type":        job.pay_type,
                    "shift_date":      str(job.shift_date),
                    "shift_duration":  shift_duration_display,
                    "work_schedule":   work_schedule,
                },
                "client_information": {
                    "client_id":      job.client.id,
                    "business_name":  business_name,
                    "business_type":  business_type,
                    "no_of_employees": no_of_employees,
                    "member_since":   member_since,
                },
                "location_and_work_type": {
                    "location":      job.location,
                    "city":          job.city,
                    "work_schedule": work_schedule,
                },
                "status": job.status,
            },
            status=status.HTTP_200_OK
        )

class JobStatusUpdateAPIView(NewAPIView):
    serializer_class = serializers.JobStatusChoicesSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['patch']

    @swagger_auto_schema(tags=["Dashboard - Job Management Page"])
    def patch(self, request, job_id):
        """
        **Update Job Status - Admin Only**\n
        Update the status of a specific job - Admin Only\n
        
        **Parameters:**
        - **job_id**: The ID of the job to update.
        
        **Request Body:**
        - **status**: The new status for the job. Choices: `draft`, `pending_approval`, `approved`, `open`, `in_progress`, `completed`, `cancelled`.
        
        **Response:**
        - **detail**: Message indicating the result of the operation.
        
        **Example Response:**
        ```json
        {
            "detail": "Job status updated successfully."
        }
        ```
        """
        from jobs.models import Job
        job = get_object_or_404(Job, id=job_id)
        job.status = request.data.get('status')
        job.save()
        return Response({"detail": "Job status updated successfully."}, status=status.HTTP_200_OK)

class AssignPhlebotomistAPIView(NewAPIView):
    serializer_class = serializers.UserIdSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['patch']

    @swagger_auto_schema(tags=["Dashboard - Job Management Page"])
    def patch(self, request, job_id):
        """
        **Assign Phlebotomist to Job - Admin Only**\n
        Assign a phlebotomist to a specific job - Admin Only\n
        
        **Parameters:**
        - **job_id**: The ID of the job to assign the phlebotomist to.
        
        **Request Body:**
        - **user_id**: The ID of the phlebotomist to assign to the job.
        
        **Response:**
        - **detail**: Message indicating the result of the operation.
        
        **Example Response:**
        ```json
        {
            "detail": "Phlebotomist assigned successfully."
        }
        ```
        """
        try:
            job = get_object_or_404(Job, id=job_id)
            if job.status == "pending_approval":
                return Response({"detail": "Job is not approved yet."}, status=status.HTTP_400_BAD_REQUEST)
            phlebotomist = get_object_or_404(User, id=request.data.get('user_id'), role="phlebotomist")
            
            overlapping_assignments = JobAssignment.objects.filter(
                phlebotomist=phlebotomist,
                status__in=[JobAssignment.ACTIVE, JobAssignment.PENDING]
            ).exclude(
                job__status__in=[Job.COMPLETED, Job.CANCELLED]
            ).filter(
                job__shift_date=job.shift_date,
                job__shift_start__lt=job.shift_end,
                job__shift_end__gt=job.shift_start
            ).exclude(job=job)

            if overlapping_assignments.exists():
                return Response(
                    {"detail": "Phlebotomist is already scheduled for another active job at this time."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            job.status = Job.IN_PROGRESS
            job.save()
            job_assignment = JobAssignment.objects.create(job=job, phlebotomist=phlebotomist, client=job.client)
            job_assignment.status = JobAssignment.ACTIVE
            job_assignment.save()
            return Response({"detail": "Phlebotomist assigned successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Dispute management views
class DisputeManagementStatisticsAPIView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['Dashboard - Dispute Management'])
    def get(self, request):
        """
        **Dispute Management Statistics - Admin Only**\n
        Retrieve dispute management statistics count including pending issues, under review, and resolved today.

        **Response Example:**
        ```json
        {
            "pending_issues": 12,
            "under_review": 5,
            "resolved_today": 8,
            "pending_issues_count": 12,
            "under_review_count": 5,
            "resolved_today_count": 8,
            "pendingIssues": 12,
            "underReview": 5,
            "resolvedToday": 8
        }
        ```
        """
        from communication.models import Report
        from django.utils import timezone

        db_pending = Report.objects.filter(status=Report.PENDING).count() or 0
        db_reviewed = Report.objects.filter(status=Report.REVIEWED).count() or 0
        
        today = timezone.now().date()
        db_resolved_today = Report.objects.filter(
            status=Report.RESOLVED,
            resolved_at__date=today
        ).count() or 0

        pending_count = db_pending
        reviewed_count = db_reviewed
        resolved_today_count = db_resolved_today

        data = {
            "pending_issues": pending_count,
            "under_review": reviewed_count,
            "resolved_today": resolved_today_count,
            "pending_issues_count": pending_count,
            "under_review_count": reviewed_count,
            "resolved_today_count": resolved_today_count,
            "pendingIssues": pending_count,
            "underReview": reviewed_count,
            "resolvedToday": resolved_today_count
        }
        return Response(data, status=status.HTTP_200_OK)


