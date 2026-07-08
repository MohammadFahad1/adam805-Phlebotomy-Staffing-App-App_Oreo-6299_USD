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
from authentication.permissions import IsApprovedClient
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.views import APIView
from jobs.models import Job
from jobs.serializers import JobCreateSerializer

User = get_user_model()


class JobCreateView(NewAPIView):
    serializer_class = JobCreateSerializer
    permission_classes = [IsApprovedClient]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['App (Client) - Job Posting'], request_body=JobCreateSerializer)
    def post(self, request):
        """
        **Post a New Job - Approved Clients Only**\n

        ### Required Fields:
        - `title` (string): Job title, e.g. "Phlebotomist Needed".
        - `professional_type` (string): Type of professional required. Choices: `RN` (Registered Nurse), `LPN` (Licensed Practical Nurse), `CP` (Certified Phlebotomist).
        - `description` (string): Full job description including tasks, responsibilities, and requirements.
        - `location` (string): Full address or clinic location.
        - `shift_date` (date): Date of the shift in `YYYY-MM-DD` format.
        - `shift_start` (time): Shift start time in `HH:MM` (24-hour) format.
        - `shift_end` (time): Shift end time in `HH:MM` (24-hour) format.
        - `pay_type` (string): Payment structure. Choices: `hourly`, `flat_rate`.
        - `pay_rate` (decimal): Compensation amount, e.g. `25.00`.
        - `job_type` (string): Type of job. Choices: `urgent`, `full_day`, `part_time`.

        ### Optional Fields:
        - `city` (string): City where the job is located.
        - `shift_duration` (integer): Estimated shift duration in hours. Defaults to `0` if omitted.

        ### Notes:
        - `job_id` is auto-generated in the format `#JB-YY-NNNNNN` and returned in the response.
        - Job is created with status `pending_approval` by default.

        ### Example Request:
        ```json
        {
            "title": "Phlebotomist Needed",
            "professional_type": "CP",
            "description": "Describe the required tasks, responsibilities, and any specific requirements.",
            "location": "123 Main Street, Suite 4",
            "city": "New York",
            "shift_date": "2025-09-01",
            "shift_start": "09:00",
            "shift_end": "18:00",
            "shift_duration": 9,
            "pay_type": "hourly",
            "pay_rate": "30.00",
            "job_type": "full_day"
        }
        ```

        ### Example Success Response:
        ```json
        {
            "message": "Job posted successfully and is pending admin approval.",
            "job_id": "JB-2025-0001"
        }
        ```

        ### Responses:
        - **201 Created**: Job posted successfully.
        - **400 Bad Request**: Validation error on one or more fields.
        - **403 Forbidden**: User is not an approved client or account is suspended.
        """
        from rest_framework import serializers as drf_serializers

        # ── Inline validation ─────────────────────────────────────────────────
        data = request.data

        errors = {}

        # Required text fields
        required_fields = ['title', 'professional_type', 'description', 'location', 'shift_date', 'shift_start', 'shift_end', 'pay_type', 'pay_rate', 'job_type']
        for field in required_fields:
            if not data.get(field):
                errors[field] = ["This field is required."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Validate choices
        valid_professional_types = [c[0] for c in Job.PROFESSIONAL_TYPE_CHOICES]
        if data.get('professional_type') not in valid_professional_types:
            errors['professional_type'] = [f"Invalid choice. Valid options: {valid_professional_types}"]

        valid_pay_types = [c[0] for c in Job.PAY_TYPE_CHOICES]
        if data.get('pay_type') not in valid_pay_types:
            errors['pay_type'] = [f"Invalid choice. Valid options: {valid_pay_types}"]

        valid_job_types = [c[0] for c in Job.JOB_TYPE_CHOICES]
        if data.get('job_type') not in valid_job_types:
            errors['job_type'] = [f"Invalid choice. Valid options: {valid_job_types}"]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Validate date and time formats
        import datetime
        try:
            shift_date = datetime.date.fromisoformat(data['shift_date'])
        except ValueError:
            errors['shift_date'] = ["Invalid date format. Use YYYY-MM-DD."]

        try:
            shift_start = datetime.time.fromisoformat(data['shift_start'])
        except ValueError:
            errors['shift_start'] = ["Invalid time format. Use HH:MM."]

        try:
            shift_end = datetime.time.fromisoformat(data['shift_end'])
        except ValueError:
            errors['shift_end'] = ["Invalid time format. Use HH:MM."]

        try:
            from decimal import Decimal, InvalidOperation
            pay_rate = Decimal(str(data['pay_rate']))
            if pay_rate < 0:
                errors['pay_rate'] = ["Pay rate must be a positive value."]
        except InvalidOperation:
            errors['pay_rate'] = ["Enter a valid decimal number."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Validate shift times are logical
        if 'shift_start' not in errors and 'shift_end' not in errors:
            if shift_end <= shift_start:
                errors['shift_end'] = ["Shift end time must be after shift start time."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # Use provided duration or calculate from shift times
        if data.get('shift_duration'):
            shift_duration = int(data['shift_duration'])
        else:
            delta = datetime.datetime.combine(datetime.date.min, shift_end) - datetime.datetime.combine(datetime.date.min, shift_start)
            shift_duration = int(delta.total_seconds() // 3600)

        job = Job.objects.create(
            client=request.user,
            title=data['title'].strip(),
            professional_type=data['professional_type'],
            description=data['description'].strip(),
            location=data['location'].strip(),
            city=data.get('city', '').strip() or None,
            shift_date=shift_date,
            shift_start=shift_start,
            shift_end=shift_end,
            shift_duration=shift_duration,
            pay_type=data['pay_type'],
            pay_rate=pay_rate,
            job_type=data['job_type'],
            status=Job.PENDING_APPROVAL,
        )

        return Response(
            {
                "message": "Job posted successfully and is pending admin approval.",
                "job_id": job.id,
            },
            status=status.HTTP_201_CREATED,
        )

