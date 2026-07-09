from phlebotomy_staffing.base import AutoPaginatedResponse, NewAPIView
from rest_framework.response import Response
from rest_framework import status
from appointments import serializers
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from authentication.serializers import EmptySerializer
from authentication.models import Client, ClientDocument, Phlebotomist, Phlebotomist_document
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.views import APIView
from appointments.models import Appointment, PatientProfile, ServicePackage, ServicePackageFeature, Payment

User = get_user_model()

class ServicePackageListView(NewAPIView):
    serializer_class = serializers.ServicePackageListSerializer
    permission_classes = [AllowAny]
    http_method_names = ['get']
    
    @swagger_auto_schema(tags=["Website - Appointments"])
    def get(self, request):
        """
        **Get All Service Packages - Public**
        
        This endpoint retrieves all service packages available for booking.
        
        ### Response Format:
        Returns a paginated list of service packages with their details and features.
        
        ### Service Package Object Structure:
        ```json
        {
            "id": 1,
            "icon": "fa fa-flask",
            "name": "Basic Health Checkup",
            "description": "Comprehensive health checkup including blood pressure, cholesterol, and glucose levels.",
            "price": 150.0,
            "is_active": true,
            "features": [
                {
                    "id": 101,
                    "name": "Blood Pressure Monitoring"
                },
                {
                    "id": 102,
                    "name": "Cholesterol Test"
                },
                {
                    "id": 103,
                    "name": "Glucose Monitoring"
                }
            ],
            "created_at": "2023-01-15T10:00:00Z",
            "updated_at": "2023-01-15T10:00:00Z"
        }
        ```
        """
        queryset = ServicePackage.objects.all()
        serializer = serializers.ServicePackageListSerializer(queryset, many=True, context={"request": request})
        return AutoPaginatedResponse(serializer.data, request)

class CreateAppointmentView(NewAPIView):
    serializer_class = serializers.AppointmentCreateSerializer
    permission_classes = [AllowAny]
    http_method_names = ['post']
    
    @swagger_auto_schema(tags=["Website - Appointments"], request_body=serializers.AppointmentCreateSerializer)
    def post(self, request):
        """
        **Create a new appointment - Public**\n
        Create a new appointment using existing service package.

        ### Request Data Format:
        This endpoint supports both JSON (`application/json`) payloads and Multipart (`multipart/form-data`) uploads.
        Patient details can be passed as flat parameters at the root level or nested inside a `patient` dictionary.

        ### Required Fields:
        - `first_name` (string): Patient's first name.
        - `last_name` (string): Patient's last name.
        - `email` (string): Patient's contact email.
        - `phone_number` (string): Patient's phone number.
        - `dob` (date): Patient's date of birth in YYYY-MM-DD format.
        - `gender` (string): Patient's gender (choices: `male`, `female`).
        - `service_package` (integer): ID of the service package to book.
        - `appointment_date` (date): Selected date for appointment (YYYY-MM-DD). Must not be in the past.
        - `start_time` (time): Selected start time (HH:MM:SS or HH:MM).
        - `location_type` (string): Type of location (choices: `home`, `hospital`, `lab`).
        - `location` (string): The street address or clinic details.
        - `consent_communication` (boolean): Required to be True.

        ### Optional Fields:
        - `end_time` (time): Selected end time.
        - `current_medications` (string): Text describing current medications.
        - `prescription` (file/string): Prescription file upload (max 5MB, PDF/JPG/JPEG/PNG) or string.
        - `known_allergies` (string): Text describing known allergies.
        - `medical_conditions` (list/string): List of selected conditions.
        - `special_requests` (string): Special requests description.
        - `email_result_notification` (boolean): Receive results via email.
        - `sms_appointment_reminders` (boolean): Receive reminders via SMS.
        """
        import datetime
        import json
        from rest_framework import serializers as drf_serializers
        
        # 1. Clone request data to make it mutable without triggering deepcopy on files
        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = dict(request.data)
        data.update(request.FILES)

        # 3. Prescription validations (File Size < 5MB and extension in PDF, JPG, JPEG, PNG)
        prescription = request.FILES.get('prescription') or data.get('prescription')
        if prescription and not isinstance(prescription, str):
            if hasattr(prescription, 'size') and prescription.size > 5 * 1024 * 1024:
                return Response({'prescription': ['File size must not exceed 5MB.']}, status=status.HTTP_400_BAD_REQUEST)
            if hasattr(prescription, 'name'):
                ext = prescription.name.split('.')[-1].lower()
                if ext not in ['pdf', 'jpg', 'jpeg', 'png']:
                    return Response({'prescription': ['Invalid file format. Only PDF, JPG, JPEG are allowed.']}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Map location_type choices
        location_type = data.get('location_type')
        if isinstance(location_type, str):
            loc_lower = location_type.lower()
            if 'home' in loc_lower:
                data['location_type'] = 'home'
            elif 'hospital' in loc_lower or 'clinic' in loc_lower:
                data['location_type'] = 'hospital'
            elif 'lab' in loc_lower:
                data['location_type'] = 'lab'

        # 5. Handle flattening if patient nested payload is received
        if 'patient' in data and isinstance(data['patient'], dict):
            patient_dict = data['patient']
            for key, val in patient_dict.items():
                data[key] = val

        # Map common variations/aliases
        if 'first_name' not in data and 'firstName' in data:
            data['first_name'] = data['firstName']
        if 'last_name' not in data and 'lastName' in data:
            data['last_name'] = data['lastName']
        if 'email' not in data and 'email_address' in data:
            data['email'] = data['email_address']
        if 'email' not in data and 'emailAddress' in data:
            data['email'] = data['emailAddress']
        if 'phone_number' not in data and 'phoneNumber' in data:
            data['phone_number'] = data['phoneNumber']
        if 'dob' not in data and 'date_of_birth' in data:
            data['dob'] = data['date_of_birth']
        if 'dob' not in data and 'dateOfBirth' in data:
            data['dob'] = data['dateOfBirth']

        # 6. Map and handle multiple medical conditions choices
        medical_conditions = data.get('medical_conditions')
        if isinstance(medical_conditions, str) and (medical_conditions.startswith('[') or medical_conditions.startswith('{')):
            try:
                medical_conditions = json.loads(medical_conditions)
            except ValueError:
                pass
        
        if isinstance(medical_conditions, list):
            mapped_conditions = []
            for cond in medical_conditions:
                if not cond:
                    continue
                cond_str = str(cond).strip()
                if cond_str.lower() in ['thyroid disorder', 'thyroid']:
                    mapped_conditions.append('Thyroid')
                elif cond_str.lower() in ['diabetes']:
                    mapped_conditions.append('Diabetes')
                elif cond_str.lower() in ['high blood pressure']:
                    mapped_conditions.append('High Blood Pressure')
                elif cond_str.lower() in ['low blood pressure']:
                    mapped_conditions.append('Low Blood Pressure')
                elif cond_str.lower() in ['heart disease']:
                    mapped_conditions.append('Heart Disease')
            if mapped_conditions:
                data['medical_conditions'] = ', '.join(mapped_conditions)
            else:
                data['medical_conditions'] = 'No Medical Conditions'
        elif isinstance(medical_conditions, str):
            cond_str = medical_conditions.strip()
            if cond_str.lower() in ['thyroid disorder', 'thyroid']:
                data['medical_conditions'] = 'Thyroid'
            elif not cond_str:
                data['medical_conditions'] = 'No Medical Conditions'
            else:
                data['medical_conditions'] = cond_str
        else:
            data['medical_conditions'] = 'No Medical Conditions'

        # 7. Map notification preferences
        email_notif = data.get('email_result_notification') or data.get('email_results_notification') or data.get('emailResultNotification') or data.get('emailResultsNotification')
        if email_notif is not None:
            data['email_result_notification'] = str(email_notif).lower() in ['true', '1', 'on']
        
        sms_notif = data.get('sms_appointment_reminders') or data.get('smsAppointmentReminders') or data.get('sms_reminders')
        if sms_notif is not None:
            data['sms_appointment_reminders'] = str(sms_notif).lower() in ['true', '1', 'on']

        # 8. Validate appointment date is not in the past
        appointment_date_str = data.get('appointment_date')
        if appointment_date_str:
            try:
                if isinstance(appointment_date_str, str):
                    app_date = datetime.datetime.strptime(appointment_date_str, "%Y-%m-%d").date()
                else:
                    app_date = appointment_date_str
                if app_date < datetime.date.today():
                    return Response({'appointment_date': ['Appointment date cannot be in the past.']}, status=status.HTTP_400_BAD_REQUEST)
            except ValueError:
                pass

        # 9. Instantiate serializer and dynamically override optional/blank fields
        serializer = self.get_serializer(data=data)
        
        prescription_file = request.FILES.get('prescription')

        if prescription_file is not None:
            serializer.fields['prescription'] = drf_serializers.FileField(required=False, allow_null=True)
            data['prescription'] = prescription_file  # ensure it's the real object, not a stray string
        else:
            serializer.fields['prescription'] = drf_serializers.CharField(required=False, allow_null=True, allow_blank=True)
        
        # Override medical_conditions to CharField to bypass choice validation
        serializer.fields['medical_conditions'] = drf_serializers.CharField(required=False, allow_null=True, allow_blank=True)
        
        # Override fields to make them optional/nullable
        optional_fields = [
            'end_time', 'current_medications', 'prescription', 
            'known_allergies', 'medical_conditions', 'special_requests', 
            'email_result_notification', 'sms_appointment_reminders'
        ]
        for field_name in optional_fields:
            if field_name in serializer.fields:
                serializer.fields[field_name].required = False
                serializer.fields[field_name].allow_null = True
                if hasattr(serializer.fields[field_name], 'allow_blank'):
                    serializer.fields[field_name].allow_blank = True

        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # 10. Get or Create/Update Patient Profile
        patient_email = validated_data.get('email')
        patient_defaults = {
            'first_name': validated_data.get('first_name'),
            'last_name': validated_data.get('last_name'),
            'phone_number': validated_data.get('phone_number'),
            'dob': validated_data.get('dob'),
            'gender': validated_data.get('gender'),
        }
        
        patient = None
        if patient_email:
            patient = PatientProfile.objects.filter(email=patient_email).first()
            
        if patient:
            for attr, val in patient_defaults.items():
                if val is not None:
                    setattr(patient, attr, val)
            patient.save()
        else:
            patient = PatientProfile.objects.create(email=patient_email, **patient_defaults)

        # 11. Create Appointment
        appointment_fields = {
            'service_package': validated_data.get('service_package'),
            'appointment_date': validated_data.get('appointment_date'),
            'start_time': validated_data.get('start_time'),
            'end_time': validated_data.get('end_time'),
            'location_type': validated_data.get('location_type'),
            'location': validated_data.get('location'),
            'current_medications': validated_data.get('current_medications'),
            'prescription': validated_data.get('prescription') if isinstance(validated_data.get('prescription'), (str, type(None))) or hasattr(validated_data.get('prescription'), 'read') else None,
            'known_allergies': validated_data.get('known_allergies'),
            'medical_conditions': validated_data.get('medical_conditions'),
            'special_requests': validated_data.get('special_requests'),
            'email_result_notification': validated_data.get('email_result_notification') if validated_data.get('email_result_notification') is not None else True,
            'sms_appointment_reminders': validated_data.get('sms_appointment_reminders') if validated_data.get('sms_appointment_reminders') is not None else True,
        }

        appointment = Appointment.objects.create(patient=patient, **appointment_fields)

        return Response({
            'detail': 'Appointment created successfully',
            'appointment_id': appointment.id,
            'status': appointment.status
        }, status=status.HTTP_201_CREATED)

class AppointmentListView(NewAPIView):
    serializer_class = serializers.AppointmentListSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = Appointment.objects.all()
        
        user = self.request.user
        
        # Role-based filtering
        if user.role == User.CLIENT:
            queryset = queryset.none()
        
        # Date filtering
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(appointment_date__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(appointment_date__lte=end_date)
        
        return queryset.select_related(
            'patient', 
            'service_package', 
        )
    
    @swagger_auto_schema(
        tags=['Dashboard - Appointment Management'],
        manual_parameters=[
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format='date',
                description='Filter by start date (YYYY-MM-DD)'
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                format='date',
                description='Filter by end date (YYYY-MM-DD)'
            )
        ]
    )
    def get(self, request):
        """
        **List all appointments - Admin Only**\n
        - Filters by phlebotomists for logged in phlebotomists\n
        - Supports date filtering\n
        - Supports phlebotomist ID filtering\n
        ### Response Data Format:
        ```json
        [
            {
                "id": 1,
                "patient": {
                    "id": 1,
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "[EMAIL_ADDRESS]",
                    "phone_number": "+1234567890",
                    "dob": "1990-01-01",
                    "gender": "male",
                    "created_at": "2023-01-15T10:00:00Z",
                    "updated_at": "2023-01-15T10:00:00Z"
                },
                "service_package": {
                    "id": 1,
                    "icon": "fa fa-flask",
                    "name": "Basic Health Checkup",
                    "description": "Comprehensive health checkup including blood pressure, cholesterol, and glucose levels.",
                    "price": 150.0,
                    "is_active": true,
                    "features": [
                        {
                            "id": 101,
                            "name": "Blood Pressure Monitoring"
                        },
                        {
                            "id": 102,
                            "name": "Cholesterol Test"
                        },
                        {
                            "id": 103,
                            "name": "Glucose Monitoring"
                        }
                    ],
                    "created_at": "2023-01-15T10:00:00Z",
                    "updated_at": "2023-01-15T10:00:00Z"
                },
                "appointment_date": "2023-02-15",
                "start_time": "10:00:00",
                "end_time": "10:30:00",
                "location_type": "home",
                "location": "123 Main St, Anytown, USA",
                "status": "booked",
                "created_at": "2023-01-20T10:00:00Z"
            }
        ]
        ```
        """
        queryset = self.get_queryset()
        serializer = serializers.AppointmentListSerializer(queryset, many=True, context={'request': request})
        return AutoPaginatedResponse(serializer.data, request)

class AppointmentDetailView(NewAPIView):
    serializer_class = serializers.AppointmentDetailSerializer
    permission_classes = [IsAdminUser]

    def get_object(self):
        appointment_id = self.kwargs['pk']
        appointment = get_object_or_404(
            Appointment.objects.select_related('patient', 'service_package'),
            id=appointment_id
        )
        
        # Authorization check
        user = self.request.user
        if user.role == User.CLIENT:
            self.permission_denied(self.request, "You don't have access to this appointment.")
        elif user.role == User.PHLEBOTOMIST:
            # Verify the phlebotomist is assigned to this appointment
            if appointment.phlebotomist != user:
                self.permission_denied(self.request, "You don't have access to this appointment.")
        
        return appointment
    
    @swagger_auto_schema(tags=["Dashboard - Appointment Management"])
    def get(self, request, pk):
        """
        **Get Appointment Details - Admin Only**\n
        Retrieve details of a specific appointment by ID.
        
        ### Response Data Format:
        ```json
        {
            "id": 1,
            "patient": {
                "id": 1,
                "first_name": "John",
                "last_name": "Doe",
                "email": "[EMAIL_ADDRESS]",
                "phone_number": "+1234567890",
                "dob": "1990-01-01",
                "gender": "male",
                "created_at": "2023-01-15T10:00:00Z",
                "updated_at": "2023-01-15T10:00:00Z"
            },
            "service_package": {
                "id": 1,
                "icon": "fa fa-flask",
                "name": "Basic Health Checkup",
                "description": "Comprehensive health checkup including blood pressure, cholesterol, and glucose levels.",
                "price": 150.0,
                "is_active": true,
                "features": [
                    {
                        "id": 101,
                        "name": "Blood Pressure Monitoring"
                    },
                    {
                        "id": 102,
                        "name": "Cholesterol Test"
                    },
                    {
                        "id": 103,
                        "name": "Glucose Monitoring"
                    }
                ],
                "created_at": "2023-01-15T10:00:00Z",
                "updated_at": "2023-01-15T10:00:00Z"
            },
            "appointment_date": "2023-02-15",
            "start_time": "10:00:00",
            "end_time": "10:30:00",
            "location_type": "home",
            "location": "123 Main St, Anytown, USA",
            "current_medications": "Aspirin 81mg daily",
            "prescription": "https://example.com/prescription.pdf",
            "known_allergies": "Penicillin",
            "medical_conditions": [
                "High Blood Pressure"
            ],
            "special_requests": "Please arrive 10 minutes early for registration.",
            "email_result_notification": true,
            "sms_appointment_reminders": true,
            "status": "booked",
            "created_at": "2023-01-20T10:00:00Z",
            "updated_at": "2023-01-20T10:00:00Z"
        }
        ```
        """
        appointment = self.get_object()
        serializer = serializers.AppointmentDetailSerializer(appointment, context={'request': request})
        return Response(serializer.data)

