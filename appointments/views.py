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
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

User = get_user_model()

import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_appointment_checkout_session(appointment, request):
    amount_cents = int(appointment.service_package.price * 100)
    payment = Payment.objects.create(
        appointment=appointment,
        amount=appointment.service_package.price,
        payment_status=Payment.PENDING
    )
    success_url = f"{settings.SITE_URL}/api/appointments/payment-success/?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.SITE_URL}/api/appointments/payment-cancel/"
    
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"Service: {appointment.service_package.name}",
                    'description': f"Appointment booking on {appointment.appointment_date}",
                },
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'appointment_id': str(appointment.id),
            'payment_id': str(payment.id),
            'type': 'appointment'
        }
    )
    payment.stripe_payment_id = session.id
    payment.save()
    return session.url

def create_job_checkout_session(job, request):
    if job.pay_type == 'flat_rate':
        amount = job.pay_rate
    else:
        amount = job.pay_rate * job.shift_duration

    amount_cents = int(amount * 100)
    payment = Payment.objects.create(
        job=job,
        amount=amount,
        payment_status=Payment.PENDING
    )
    success_url = f"{settings.SITE_URL}/api/appointments/payment-success/?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{settings.SITE_URL}/api/appointments/payment-cancel/"

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"Job Posting: {job.title}",
                    'description': f"Shift on {job.shift_date}",
                },
                'unit_amount': amount_cents,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'job_id': str(job.id),
            'payment_id': str(payment.id),
            'type': 'job'
        }
    )
    payment.stripe_payment_id = session.id
    payment.save()
    return session.url


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

        # 2. Terms and Consent checks
        terms_agreement = data.get('terms_agreement') or data.get('terms') or data.get('termsAgreement')
        consent_communication = data.get('consent_communication') or data.get('consent') or data.get('consentCommunication')
        
        if not terms_agreement or str(terms_agreement).lower() == 'false':
            return Response({'terms_agreement': ['You must agree to the Terms of Service and Privacy Policy.']}, status=status.HTTP_400_BAD_REQUEST)
        if not consent_communication or str(consent_communication).lower() == 'false':
            return Response({'consent_communication': ['You must consent to receive appointment confirmations and results.']}, status=status.HTTP_400_BAD_REQUEST)

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

        checkout_url = create_appointment_checkout_session(appointment, request)

        return Response({
            'detail': 'Appointment created successfully',
            'appointment_id': appointment.id,
            'status': appointment.status,
            'checkout_url': checkout_url
        }, status=status.HTTP_201_CREATED)

class AppointmentListView(NewAPIView):
    serializer_class = serializers.AppointmentListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Appointment.objects.all()
        
        user = self.request.user
        
        # Role-based filtering
        if user.role == User.CLIENT:
            queryset = queryset.none()
        elif user.role == User.PHLEBOTOMIST:
            queryset = queryset.filter(jobs__assignment__phlebotomist=user)
        
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
    permission_classes = [IsAuthenticated]

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
            from jobs.models import JobAssignment
            is_assigned = JobAssignment.objects.filter(
                phlebotomist=user,
                job__appointment=appointment
            ).exists()
            if not is_assigned:
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

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Stripe Webhook - Don't use these."])
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            metadata = session.get('metadata', {})
            payment_type = metadata.get('type')
            payment_id = metadata.get('payment_id')

            try:
                payment = Payment.objects.get(id=payment_id)
            except Payment.DoesNotExist:
                return Response({'error': 'Payment not found'}, status=status.HTTP_400_BAD_REQUEST)

            payment.payment_status = Payment.PAID
            payment.stripe_payment_id = session.id
            payment.save()

            if payment_type == 'appointment':
                appointment_id = metadata.get('appointment_id')
                try:
                    appointment = Appointment.objects.get(id=appointment_id)
                    appointment.status = Appointment.CONFIRMED
                    appointment.save()
                except Appointment.DoesNotExist:
                    pass
            elif payment_type == 'job':
                job_id = metadata.get('job_id')
                try:
                    from jobs.models import Job
                    job = Job.objects.get(id=job_id)
                    job.status = Job.APPROVED
                    job.save()
                except Job.DoesNotExist:
                    pass

        return Response({'success': True}, status=status.HTTP_200_OK)

class PaymentSuccessView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Stripe Webhook - Don't use these."])
    def get(self, request):
        session_id = request.query_params.get('session_id')
        if session_id:
            try:
                session = stripe.checkout.Session.retrieve(session_id)
                metadata = session.get('metadata', {})
                payment_id = metadata.get('payment_id')
                payment_type = metadata.get('type')
                
                try:
                    payment = Payment.objects.get(id=payment_id)
                    if payment.payment_status != Payment.PAID:
                        payment.payment_status = Payment.PAID
                        payment.stripe_payment_id = session_id
                        payment.save()

                        if payment_type == 'appointment':
                            appointment_id = metadata.get('appointment_id')
                            appointment = Appointment.objects.get(id=appointment_id)
                            appointment.status = Appointment.CONFIRMED
                            appointment.save()
                        elif payment_type == 'job':
                            from jobs.models import Job
                            job_id = metadata.get('job_id')
                            job = Job.objects.get(id=job_id)
                            job.status = Job.APPROVED
                            job.save()
                except Exception:
                    pass
            except Exception:
                pass
        return Response({'message': 'Payment completed successfully.'}, status=status.HTTP_200_OK)

class PaymentCancelView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["Stripe Webhook - Don't use these."])
    def get(self, request):
        return Response({'message': 'Payment cancelled.'}, status=status.HTTP_200_OK)

class ClientInvitePhlebotomistView(NewAPIView):
    serializer_class = serializers.AppointmentUserIdSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    @swagger_auto_schema(tags=["App (Client) - Home Section"])
    def post(self, request, appointment_id):
        """
        **Client Invite Phlebotomist to Appointment**\n
        Invites/assigns a phlebotomist to a client's appointment.\n
        Auto-creates a Job in APPROVED status and a pending JobAssignment.\n
        """
        from jobs.models import Job, JobAssignment
        import random

        if request.user.role != User.CLIENT:
            return Response({"detail": "Only clients can invite phlebotomists."}, status=status.HTTP_403_FORBIDDEN)

        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Verify ownership
        if appointment.client != request.user:
            return Response({"detail": "You do not own this appointment."}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        phlebotomist = get_object_or_404(User, id=user_id, role=User.PHLEBOTOMIST)

        # Create a job with approved status
        from django.utils import timezone
        now_dt = timezone.now()
        year_suffix = now_dt.strftime("%y")
        
        random_num = random.randint(100000, 999999)
        job_id = f"JB-{year_suffix}-{random_num}"
        while Job.objects.filter(id=job_id).exists():
            random_num = random.randint(100000, 999999)
            job_id = f"JB-{year_suffix}-{random_num}"

        job_title = f"Appointment Service: {appointment.service_package.name}"
        job_desc = appointment.special_requests or f"Service package {appointment.service_package.name} booking."
        location = appointment.location
        city = location.split(',')[0] if ',' in location else location
        
        shift_duration = 1
        if appointment.end_time and appointment.start_time:
            from datetime import datetime, date
            dt1 = datetime.combine(date.today(), appointment.start_time)
            dt2 = datetime.combine(date.today(), appointment.end_time)
            diff = dt2 - dt1
            shift_duration = max(1, int(diff.total_seconds() / 3600))
            
        job = Job.objects.create(
            id=job_id,
            appointment=appointment,
            client=request.user,
            title=job_title,
            description=job_desc,
            location=location,
            city=city,
            shift_date=appointment.appointment_date,
            shift_start=appointment.start_time,
            shift_end=appointment.end_time or appointment.start_time,
            shift_duration=shift_duration,
            pay_rate=appointment.service_package.price,
            pay_type='flat_rate',
            status=Job.APPROVED
        )
        
        # Create a pending JobAssignment
        job_assignment = JobAssignment.objects.create(
            job=job,
            phlebotomist=phlebotomist,
            client=request.user,
            signed_by_client=True,
            status=JobAssignment.PENDING
        )

        return Response({"detail": "Phlebotomist invited successfully. Job created."}, status=status.HTTP_200_OK)

class WalletBalanceView(NewAPIView):
    serializer_class = serializers.WalletBalanceSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    @swagger_auto_schema(tags=["Wallet & Payments"])
    def get(self, request):
        """
        **Get Wallet Balance & Transactions**\n
        Returns the withdrawable balance, total gross earnings, total platform fees, and transaction history.
        """
        from appointments.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)

class PayoutRequestView(NewAPIView):
    serializer_class = serializers.PayoutRequestCreateSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']

    @swagger_auto_schema(tags=["Wallet & Payments"])
    def post(self, request):
        """
        **Request Payout**\n
        Requests payout/withdrawal of a specific amount from the user's wallet.
        """
        from appointments.models import Wallet, WalletTransaction, PayoutRequest
        from django.db import transaction

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data['amount']

        if amount <= 0:
            return Response({"detail": "Payout amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        if wallet.balance < amount:
            return Response({"detail": "Insufficient balance for this payout request."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            wallet.balance -= amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.DEBIT,
                amount=amount,
                description=f"Withdrawal request of ${amount}"
            )

            payout_req = PayoutRequest.objects.create(
                user=request.user,
                amount=amount,
                status=PayoutRequest.PENDING
            )

        return Response({"detail": "Payout request submitted successfully.", "payout_request_id": payout_req.id}, status=status.HTTP_200_OK)

class PatientListView(NewAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.PatientListSerializer

    @swagger_auto_schema(tags=["App - Patient Management"])
    def get(self, request):
        """
        **Get list of patients for logged-in Client or Phlebotomist**
        
        Retrieves all appointments and returns formatted patient information.
        - Clients see patients directly assigned to their appointments.
        - Phlebotomists see patients assigned to jobs they are handling.
        """
        user = request.user
        
        if user.role == User.CLIENT:
            queryset = Appointment.objects.filter(client=user)
        elif user.role == User.PHLEBOTOMIST:
            queryset = Appointment.objects.filter(jobs__assignment__phlebotomist=user)
        else:
            if user.is_staff or user.role == User.ADMIN:
                queryset = Appointment.objects.all()
            else:
                queryset = Appointment.objects.none()
                
        queryset = queryset.select_related('patient').order_by('-appointment_date', '-start_time')
        
        serializer = self.get_serializer(queryset, many=True)
        return AutoPaginatedResponse(serializer.data, request)

class PatientAppointmentDetailView(NewAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.PatientAppointmentDetailSerializer

    @swagger_auto_schema(tags=["App - Patient Management"])
    def get(self, request, pk):
        """
        **Get detailed appointment and patient information**
        
        Retrieves comprehensive information for the specific appointment detail screen.
        Checks permissions:
        - Clients can view details if the appointment belongs to them.
        - Phlebotomists can view details if they are assigned to the job associated with the appointment.
        """
        appointment = get_object_or_404(
            Appointment.objects.select_related('patient', 'service_package', 'client'),
            id=pk
        )
        
        user = request.user
        
        # Permission checks
        if not (user.is_staff or user.role == User.ADMIN):
            if user.role == User.CLIENT:
                if appointment.client != user:
                    self.permission_denied(request, "You do not have access to this appointment.")
            elif user.role == User.PHLEBOTOMIST:
                from jobs.models import JobAssignment
                is_assigned = JobAssignment.objects.filter(
                    phlebotomist=user,
                    job__appointment=appointment
                ).exists()
                if not is_assigned:
                    self.permission_denied(request, "You do not have access to this appointment.")
            else:
                self.permission_denied(request, "You do not have access to this appointment.")
                
        serializer = self.get_serializer(appointment, context={'request': request})
        return Response(serializer.data)





