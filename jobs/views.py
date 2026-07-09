from authentication.permissions import IsApprovedPhlebotomist
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
from jobs.models import Job, JobTemplate
from jobs.serializers import JobCreateSerializer
from datetime import datetime

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

class JobListForClient(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedClient]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App (Client) - Job Posting'])
    def get(self, request):
        """
        **Get Job List for Client - Approved Clients Only**\n

        Retrieve a list of jobs posted by the logged-in client, structured to support the visual listing tabs (All, New Job, Assigned, Completed) and search input.

        ### Query Parameters:
        - `filter` (string, optional): Tab selection filter. Choices: `all` (default), `new_job`, `assigned`, `completed`.
        - `search` (string, optional): Search keyword to match job title, location, or city.
        - `page` (integer, optional): Page number (default: 1).
        - `page_size` (integer, optional): Number of items per page (default: 10).

        ### Action Status (UI Action Button states):
        - `Completed`: Job is finished (`completed`).
        - `Assigned`: Phlebotomist is assigned (`in_progress`).
        - `Invite`: Job is open (`open`).
        - `Pending Approval`: Job is pending admin verification (`pending_approval`).
        - `Draft`: Job is in draft (`draft`).
        - `Cancelled`: Job has been cancelled (`cancelled`).

        ### Example Response:
        ```json
        {
            "success": true,
            "pagination": {
                "count": 1,
                "total_pages": 1,
                "current_page": 1,
                "next": null,
                "previous": null
            },
            "results": [
                {
                    "id": "JB-26-000001",
                    "title": "Blood Draw Service",
                    "business_name": "Metro General Hospital",
                    "professional_type": "Certified Phlebotomist",
                    "distance": "2.3 miles away",
                    "shift_time": "11:00 PM - 07:00 AM",
                    "shift_duration": "3 hours",
                    "shift_date": "Aug 15, 2025",
                    "pay_rate": "$30/hr",
                    "job_type": "Full Day",
                    "status": "open",
                    "action_status": "Invite",
                    "created_at": "2026-07-08 02:00:00"
                }
            ]
        }
        ```
        """
        # 1. Parse the tab filter parameter and remove it from query_params so AutoPaginatedResponse doesn't filter on it
        tab = request.query_params.get('filter', 'all').lower()
        if 'filter' in request.GET:
            qd = request.GET.copy()
            qd.pop('filter', None)
            request._request.GET = qd
            if hasattr(request, '_query_params'):
                try:
                    delattr(request, '_query_params')
                except AttributeError:
                    pass

        queryset = Job.objects.filter(client=request.user).select_related('client__client_profile')

        # 1. Apply tab-based filter
        if tab == 'new_job':
            queryset = queryset.filter(status__in=[Job.DRAFT, Job.PENDING_APPROVAL, Job.OPEN])
        elif tab == 'assigned':
            queryset = queryset.filter(status=Job.IN_PROGRESS)
        elif tab == 'completed':
            queryset = queryset.filter(status=Job.COMPLETED)

        # 2. Apply search query
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(city__icontains=search_query)
            )

        queryset = queryset.order_by('-created_at')

        # 3. Serialize data manually matching the UI specs
        data = []
        for job in queryset:
            try:
                business_name = job.client.client_profile.business_name
            except Exception:
                business_name = job.client.full_name or "Unknown Client"

            # Format shift start and end times
            start_str = job.shift_start.strftime("%I:%M %p").lstrip('0') if job.shift_start else ""
            end_str = job.shift_end.strftime("%I:%M %p").lstrip('0') if job.shift_end else ""
            shift_time = f"{start_str} - {end_str}" if start_str and end_str else ""

            # Format shift duration
            shift_dur = f"{job.shift_duration} hour{'s' if job.shift_duration != 1 else ''}"

            # Format shift date (e.g. Aug 15, 2025)
            shift_date_str = job.shift_date.strftime("%b %d, %Y") if job.shift_date else ""

            # Format pay rate
            pay_rate_formatted = f"${job.pay_rate}/{'hr' if job.pay_type == 'hourly' else 'flat'}"

            # Determine button/action status shown in UI
            if job.status == Job.COMPLETED:
                action_status = "Completed"
            elif job.status == Job.IN_PROGRESS:
                action_status = "Assigned"
            elif job.status == Job.OPEN:
                action_status = "Invite"
            elif job.status == Job.PENDING_APPROVAL:
                action_status = "Pending Approval"
            elif job.status == Job.DRAFT:
                action_status = "Draft"
            elif job.status == Job.CANCELLED:
                action_status = "Cancelled"
            else:
                action_status = job.status.replace('_', ' ').capitalize()

            prof_type_display = job.get_professional_type_display() if hasattr(job, 'get_professional_type_display') else job.professional_type
            job_type_display = job.get_job_type_display() if hasattr(job, 'get_job_type_display') else job.job_type

            data.append({
                "id": job.id,
                "title": job.title,
                "business_name": business_name,
                "professional_type": prof_type_display,
                "distance": "2.3 miles away", # Mock distance matching design specs
                "shift_time": shift_time,
                "shift_duration": shift_dur,
                "shift_date": shift_date_str,
                "pay_rate": pay_rate_formatted,
                "job_type": job_type_display,
                "status": job.status,
                "action_status": action_status,
                "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None
            })

        return AutoPaginatedResponse(data, request=request)

class JobTemplateListForClient(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedClient]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App (Client) - Job Posting'])
    def get(self, request):
        """
        **Get Job Templates - Approved Clients Only**\n

        Retrieve a list of quick job templates for clients to easily prefill job post details. Supports searching by title or description.

        ### Query Parameters:
        - `search` (string, optional): Search keyword to match template title or description.
        - `page` (integer, optional): Page number (default: 1).
        - `page_size` (integer, optional): Number of items per page (default: 10).

        ### Example Response:
        ```json
        {
            "success": true,
            "pagination": {
                "count": 1,
                "total_pages": 1,
                "current_page": 1,
                "next": null,
                "previous": null
            },
            "results": [
                {
                    "id": 1,
                    "title": "Regular Wednesday RN Shift",
                    "professional_type": "RN",
                    "shift_duration": "12-hour shift",
                    "description": "Emergency Department",
                    "last_used": "Last used 2 days ago",
                    "pay_rate": "$45.00/hr",
                    "location": "Main Campus",
                    "city": "New York",
                    "shift_start": "09:00 AM",
                    "shift_end": "09:00 PM",
                    "job_type": "Full Day"
                }
            ]
        }
        ```
        """
        queryset = JobTemplate.objects.all()

        search_query = request.query_params.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        queryset = queryset.order_by('-created_at')

        # Relativetime helper for last_used mock or using updated_at
        from django.utils.timezone import now
        from datetime import timedelta
        def get_last_used_str(dt):
            if not dt:
                return "Last used 2 days ago"
            delta = now() - dt
            if delta < timedelta(minutes=60):
                return "Last used just now"
            elif delta < timedelta(hours=24):
                h = int(delta.total_seconds() // 3600)
                return f"Last used {h} hour{'s' if h != 1 else ''} ago"
            else:
                d = delta.days
                if d == 1:
                    return "Last used 1 day ago"
                elif d < 7:
                    return f"Last used {d} days ago"
                else:
                    w = d // 7
                    return f"Last used {w} week{'s' if w != 1 else ''} ago"

        data = []
        for template in queryset:
            prof_type = template.professional_type
            if prof_type == 'CP':
                prof_display = 'Phlebotomist'
            elif prof_type == 'RN':
                prof_display = 'RN'
            elif prof_type == 'LPN':
                prof_display = 'LPN'
            else:
                prof_display = template.get_professional_type_display() if hasattr(template, 'get_professional_type_display') else template.professional_type

            shift_dur_str = f"{template.shift_duration}-hour shift"
            pay_rate_formatted = f"${template.pay_rate}/{'hr' if template.pay_type == 'hourly' else 'flat'}"

            data.append({
                "id": template.id,
                "title": template.title,
                "professional_type": prof_display,
                "shift_duration": shift_dur_str,
                "description": template.description.strip(),
                "last_used": get_last_used_str(template.updated_at),
                "pay_rate": pay_rate_formatted,
                "location": template.location,
                "city": template.city,
                "shift_start": template.shift_start.strftime("%I:%M %p") if template.shift_start else "",
                "shift_end": template.shift_end.strftime("%I:%M %p") if template.shift_end else "",
                "job_type": template.get_job_type_display() if hasattr(template, 'get_job_type_display') else template.job_type,
            })

        return AutoPaginatedResponse(data, request=request)

class JobTemplateDetailView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedClient]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App (Client) - Job Posting'])
    def get(self, request, pk):
        """
        **Get Job Template Details**\n

        Retrieve a single job template by its ID.

        ### Path Parameters:
        - `pk` (integer, required): The ID of the job template to retrieve.

        ### Example Response:
        ```json
        {
            "success": true,
            "data": {
                "id": 1,
                "title": "Regular Wednesday RN Shift",
                "professional_type": "RN",
                "shift_duration": "12-hour shift",
                "description": "Emergency Department",
                "last_used": "Last used 2 days ago",
                "pay_rate": "$45.00/hr",
                "location": "Main Campus",
                "city": "New York",
                "shift_start": "09:00 AM",
                "shift_end": "09:00 PM",
                "job_type": "Full Day"
            }
        }
        ```
        """
        try:
            job_template = JobTemplate.objects.get(pk=pk)
        except JobTemplate.DoesNotExist:
            return Response({
                "success": False,
                "message": "Template not found",
            }, status=status.HTTP_404_NOT_FOUND)

        # Relativetime helper for last_used
        from django.utils.timezone import now
        from datetime import timedelta
        def get_last_used_str(dt):
            if not dt:
                return "Last used 2 days ago"
            delta = now() - dt
            if delta < timedelta(minutes=60):
                return "Last used just now"
            elif delta < timedelta(hours=24):
                h = int(delta.total_seconds() // 3600)
                return f"Last used {h} hour{'s' if h != 1 else ''} ago"
            else:
                d = delta.days
                if d == 1:
                    return "Last used 1 day ago"
                elif d < 7:
                    return f"Last used {d} days ago"
                else:
                    w = d // 7
                    return f"Last used {w} week{'s' if w != 1 else ''} ago"

        prof_type = job_template.professional_type
        if prof_type == 'CP':
            prof_display = 'Phlebotomist'
        elif prof_type == 'RN':
            prof_display = 'RN'
        elif prof_type == 'LPN':
            prof_display = 'LPN'
        else:
            prof_display = job_template.get_professional_type_display() if hasattr(job_template, 'get_professional_type_display') else job_template.professional_type

        shift_dur_str = f"{job_template.shift_duration}-hour shift"
        pay_rate_formatted = f"${job_template.pay_rate}/{'hr' if job_template.pay_type == 'hourly' else 'flat'}"

        data = {
            "id": job_template.id,
            "title": job_template.title,
            "professional_type": prof_display,
            "shift_duration": shift_dur_str,
            "description": job_template.description.strip(),
            "last_used": get_last_used_str(job_template.updated_at),
            "pay_rate": pay_rate_formatted,
            "location": job_template.location,
            "city": job_template.city,
            "shift_start": job_template.shift_start.strftime("%I:%M %p") if job_template.shift_start else "",
            "shift_end": job_template.shift_end.strftime("%I:%M %p") if job_template.shift_end else "",
            "job_type": job_template.get_job_type_display() if hasattr(job_template, 'get_job_type_display') else job_template.job_type,
        }

        return Response({
            "success": True,
            "data": data
        })


# Phlebotomist Endpoints
class PhlebotomistAvailableJobsAPIView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedPhlebotomist]
    http_method_names = ['get']
    @swagger_auto_schema(tags=['App (Phlebotomist) - Home Section'])
    def get(self, request):
        """
        **Get Available Jobs for Phlebotomist - Phlebotomist**\n
        Retrieve a list of open/approved jobs that the phlebotomist can apply to.

        ### Parameters:
        - `filter` (string, optional): Filter by tab. Possible values: 'all', 'near_me', 'night_shift', 'today'.
        - `search` (string, optional): Search query.

        ### Example:
        ```http
        GET /api/jobs/phlebotomist/available/?filter=near_me&search=New+York
        {
        "success": true,
        "pagination": {
            "count": 4,
            "total_pages": 1,
            "current_page": 1,
            "next": null,
            "previous": null
        },
        "results": [
                {
                    "id": "JB-26-000006",
                    "title": "ICU Nurse - Night Shift",
                    "business_name": "Metro General Hospital",
                    "professional_type": "Phlebotomist",
                    "distance": "2.3 miles away",
                    "shift_time": "11:00 PM - 7:00 AM",
                    "shift_duration": "3 hours",
                    "shift_date": "Aug 15, 2025",
                    "pay_rate": "$30.00/hr",
                    "location": "Metro General Hospital",
                    "city": "New York",
                    "job_type": "Part Time",
                    "description": "Overnight ICU nurse staffing.",
                    "status": "open",
                    "applied": false,
                    "action_status": "Apply",
                    "created_at": "2026-07-09 11:34:19"
                },
                {
                    "id": "JB-26-000005",
                    "title": "ICU Nurse",
                    "business_name": "Metro General Hospital",
                    "professional_type": "Phlebotomist",
                    "distance": "2.3 miles away",
                    "shift_time": "11:00 PM - 7:00 AM",
                    "shift_duration": "3 hours",
                    "shift_date": "Aug 15, 2025",
                    "pay_rate": "$30.00/hr",
                    "location": "Metro General Hospital",
                    "city": "New York",
                    "job_type": "Full Day",
                    "description": "Critical care nursing support.",
                    "status": "open",
                    "applied": true,
                    "action_status": "Applied",
                    "created_at": "2026-07-09 11:34:19"
                }
            ]
        }
        ```
        """
        # pyrefly: ignore [missing-import]
        from django.db.models import Q
        from jobs.models import Job, JobAssignment, JobApplication

        # 1. Fetch job ids with assignments that are ACTIVE, COMPLETED, or DISPUTED
        assigned_job_ids = JobAssignment.objects.filter(
            status__in=[JobAssignment.ACTIVE, JobAssignment.COMPLETED, JobAssignment.DISPUTED]
        ).values_list('job_id', flat=True)

        # 2. Get approved/open jobs not in that list
        queryset = Job.objects.filter(
            status__in=[Job.APPROVED, Job.OPEN]
        ).exclude(
            id__in=assigned_job_ids
        )

        # 3. Filter by tab
        tab = request.query_params.get('filter', 'all').lower().replace(' ', '_')
        if 'filter' in request.GET:
            qd = request.GET.copy()
            qd.pop('filter', None)
            request._request.GET = qd
            if hasattr(request, '_query_params'):
                try:
                    delattr(request, '_query_params')
                except AttributeError:
                    pass

        if tab == 'near_me':
            try:
                profile = request.user.phlebotomist_profile
                if profile.service_area:
                    queryset = queryset.filter(
                        Q(city__icontains=profile.service_area) | 
                        Q(location__icontains=profile.service_area)
                    )
            except Exception:
                pass
        elif tab == 'night_shift':
            import datetime
            queryset = queryset.filter(
                Q(shift_start__gte=datetime.time(18, 0)) |
                Q(shift_start__lte=datetime.time(6, 0))
            )
        elif tab == 'today':
            from django.utils import timezone
            queryset = queryset.filter(shift_date=timezone.localdate())

        # 4. Filter by search
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(professional_type__icontains=search_query)
            )

        queryset = queryset.order_by('-created_at')

        # 5. Fetch applied jobs for the requesting user
        applied_job_ids = set(
            JobApplication.objects.filter(phlebotomist=request.user)
            .values_list('job_id', flat=True)
        )

        data = []
        for job in queryset:
            try:
                business_name = job.client.client_profile.business_name
            except Exception:
                business_name = job.client.full_name or "Unknown Client"

            # Format shift times
            start_str = job.shift_start.strftime("%I:%M %p").lstrip('0') if job.shift_start else ""
            end_str = job.shift_end.strftime("%I:%M %p").lstrip('0') if job.shift_end else ""
            shift_time = f"{start_str} - {end_str}" if start_str and end_str else ""

            # Format shift duration
            shift_dur = f"{job.shift_duration} hour{'s' if job.shift_duration != 1 else ''}"

            # Format shift date (e.g. Aug 15, 2025)
            shift_date_str = job.shift_date.strftime("%b %d, %Y") if job.shift_date else ""

            # Format pay rate
            pay_rate_formatted = f"${job.pay_rate}/{'hr' if job.pay_type == 'hourly' else 'flat'}"

            # Format professional type display
            if job.professional_type == 'CP':
                prof_display = 'Phlebotomist'
            elif job.professional_type == 'RN':
                prof_display = 'RN'
            elif job.professional_type == 'LPN':
                prof_display = 'LPN'
            else:
                prof_display = job.get_professional_type_display() if hasattr(job, 'get_professional_type_display') else job.professional_type

            job_type_display = job.get_job_type_display() if hasattr(job, 'get_job_type_display') else job.job_type

            is_applied = job.id in applied_job_ids
            action_status = "Applied" if is_applied else "Apply"

            data.append({
                "id": job.id,
                "title": job.title,
                "business_name": business_name,
                "professional_type": prof_display,
                "distance": "2.3 miles away", # Mock distance matching design specs
                "shift_time": shift_time,
                "shift_duration": shift_dur,
                "shift_date": shift_date_str,
                "pay_rate": pay_rate_formatted,
                "location": job.location,
                "city": job.city,
                "job_type": job_type_display,
                "description": job.description,
                "status": job.status,
                "applied": is_applied,
                "action_status": action_status,
                "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None
            })

        response = AutoPaginatedResponse(data, request=request)
        # if isinstance(response.data, dict) and 'results' in response.data:
        #     response.data['data'] = response.data['results']
        return response

class PhlebotomistAppliedJobsAPIView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedPhlebotomist]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App (Phlebotomist) - Home Section'])
    def get(self, request):
        """
        **Get Applied Jobs for Phlebotomist - Phlebotomist**\n
        Retrieve a list of jobs that the phlebotomist has applied to.
        """
        from django.db.models import Q
        from jobs.models import Job, JobApplication

        # 1. Fetch job ids applied to by the requesting user
        applied_job_ids = JobApplication.objects.filter(phlebotomist=request.user).values_list('job_id', flat=True)

        # 2. Filter jobs in that list
        queryset = Job.objects.filter(id__in=applied_job_ids)

        # 3. Filter by tab
        tab = request.query_params.get('filter', 'all').lower().replace(' ', '_')
        if 'filter' in request.GET:
            qd = request.GET.copy()
            qd.pop('filter', None)
            request._request.GET = qd
            if hasattr(request, '_query_params'):
                try:
                    delattr(request, '_query_params')
                except AttributeError:
                    pass

        if tab == 'near_me':
            try:
                profile = request.user.phlebotomist_profile
                if profile.service_area:
                    queryset = queryset.filter(
                        Q(city__icontains=profile.service_area) | 
                        Q(location__icontains=profile.service_area)
                    )
            except Exception:
                pass
        elif tab == 'night_shift':
            import datetime
            queryset = queryset.filter(
                Q(shift_start__gte=datetime.time(18, 0)) |
                Q(shift_start__lte=datetime.time(6, 0))
            )
        elif tab == 'today':
            from django.utils import timezone
            queryset = queryset.filter(shift_date=timezone.localdate())

        # 4. Filter by search
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(professional_type__icontains=search_query)
            )

        queryset = queryset.order_by('-created_at')

        data = []
        for job in queryset:
            try:
                business_name = job.client.client_profile.business_name
            except Exception:
                business_name = job.client.full_name or "Unknown Client"

            # Format shift times
            start_str = job.shift_start.strftime("%I:%M %p").lstrip('0') if job.shift_start else ""
            end_str = job.shift_end.strftime("%I:%M %p").lstrip('0') if job.shift_end else ""
            shift_time = f"{start_str} - {end_str}" if start_str and end_str else ""

            # Format shift duration
            shift_dur = f"{job.shift_duration} hour{'s' if job.shift_duration != 1 else ''}"

            # Format shift date
            shift_date_str = job.shift_date.strftime("%b %d, %Y") if job.shift_date else ""

            # Format pay rate
            pay_rate_formatted = f"${job.pay_rate}/{'hr' if job.pay_type == 'hourly' else 'flat'}"

            # Format professional type display
            if job.professional_type == 'CP':
                prof_display = 'Phlebotomist'
            elif job.professional_type == 'RN':
                prof_display = 'RN'
            elif job.professional_type == 'LPN':
                prof_display = 'LPN'
            else:
                prof_display = job.get_professional_type_display() if hasattr(job, 'get_professional_type_display') else job.professional_type

            job_type_display = job.get_job_type_display() if hasattr(job, 'get_job_type_display') else job.job_type

            data.append({
                "id": job.id,
                "title": job.title,
                "business_name": business_name,
                "professional_type": prof_display,
                "distance": "2.3 miles away",
                "shift_time": shift_time,
                "shift_duration": shift_dur,
                "shift_date": shift_date_str,
                "pay_rate": pay_rate_formatted,
                "location": job.location,
                "city": job.city,
                "job_type": job_type_display,
                "description": job.description,
                "status": job.status,
                "applied": True,
                "action_status": "Applied",
                "created_at": job.created_at.strftime("%Y-%m-%d %H:%M:%S") if job.created_at else None
            })

        response = AutoPaginatedResponse(data, request=request)
        return response

class PhlebotomistJobApplyView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedPhlebotomist]
    http_method_names = ['post']

    @swagger_auto_schema(tags=['App (Phlebotomist) - Home Section'])
    def post(self, request, job_id):
        """
        **Apply for a Job - Phlebotomist**\n
        Apply to an open/approved job if no scheduling conflict exists and no phlebotomist is assigned.

        ### Path Parameters:
        - `job_id` (string, required): The ID of the job to apply for.

        ### Example Response:
        ```json
        {
            "detail": "Job application submitted successfully."
        }
        ```

        ### Error Responses:
        - `400 Bad Request`: If the job is not in a state where it can be applied to (e.g., draft, pending, in progress, completed, cancelled).
        - `400 Bad Request`: If a phlebotomist is already assigned to this job.
        - `400 Bad Request`: If the phlebotomist has a schedule conflict with another active job.
        - `400 Bad Request`: If the phlebotomist has already applied to this job.
        """
        from jobs.models import Job, JobAssignment, JobApplication

        job = get_object_or_404(Job, id=job_id)

        # 1. Job Status check: cannot apply if draft, pending approval, in progress, completed, or cancelled
        if job.status in [Job.DRAFT, Job.PENDING_APPROVAL, Job.IN_PROGRESS, Job.COMPLETED, Job.CANCELLED]:
            return Response(
                {"detail": f"Cannot apply to a job with status: {job.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Check if a phlebotomist is already assigned to this job
        if JobAssignment.objects.filter(job=job).exists():
            return Response(
                {"detail": "A phlebotomist is already assigned to this job."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Check for schedule conflict
        overlapping_assignments = JobAssignment.objects.filter(
            phlebotomist=request.user,
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
                {"detail": "You have a schedule conflict with another active job at this time."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Check if already applied
        if JobApplication.objects.filter(job=job, phlebotomist=request.user).exists():
            return Response(
                {"detail": "You have already applied to this job."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 5. Create Job Application
        JobApplication.objects.create(
            job=job,
            phlebotomist=request.user,
            status=JobApplication.PENDING
        )

        return Response(
            {"detail": "Job application submitted successfully."},
            status=status.HTTP_201_CREATED
        )

class PhlebotomistJobDetailsAPIView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedPhlebotomist]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App (Phlebotomist) - Home Section'])
    def get(self, request, job_id):
        """
        **Get Job Details for Phlebotomist**\n
        Retrieve a detailed view of a job for a phlebotomist.

        Path Parameters:
        - `job_id` (string, required): The ID of the job to retrieve details for.

        Example Response:
        ```json
        {
            "success": true,
            "id": "JB-26-000004",
            "title": "Physical Therapist",
            "description": "Physical therapy support.",
            "status": "open",
            "applied": true,
            "application_status": "pending",
            "client_name": "Faysal Munshi",
            "client_address": "Bir Sreshtho AK Khandokar Road, Mohakhali, Dhaka, Bangladesh 1212",
            "client_business_name": "(Metro General Hospital)",
            "client_phone": "01772211521",
            "shift_date": "August 15, 2025",
            "shift_time": "11:00 PM - 7:00 AM (3 hours)",
            "formatted_job_id": "#JB-26-000004",
            "hourly_rate": "$30.00",
            "total_hours": "3.0 hrs",
            "subtotal": "$90.00",
            "service_fee": "-$4.50",
            "tax_withholding": "-$13.50",
            "total_earnings": "$72.00",
            "client_info": {
                "name": "Faysal Munshi",
                "role": "Client",
                "address": "Bir Sreshtho AK Khandokar Road, Mohakhali, Dhaka, Bangladesh 1212",
                "business_name": "(Metro General Hospital)",
                "phone": "01772211521"
            },
            "job_details": {
                "title": "Physical Therapist",
                "shift_date": "August 15, 2025",
                "shift_time": "11:00 PM - 7:00 AM (3 hours)",
                "formatted_job_id": "#JB-26-000004",
                "description": "Physical therapy support."
            },
            "payment_breakdown": {
                "hourly_rate": "$30.00",
                "total_hours": "3.0 hrs",
                "subtotal": "$90.00",
                "service_fee": "-$4.50",
                "tax_withholding": "-$13.50",
                "total_earnings": "$72.00"
            }
        }
        ```

        Error Responses:
        - 404 Not Found: If the job with the specified ID does not exist.
        - 403 Forbidden: If the user is not authenticated or not an approved phlebotomist.
        """
        from jobs.models import Job
        from django.shortcuts import get_object_or_404

        job = get_object_or_404(Job, id=job_id)

        try:
            client_profile = job.client.client_profile
            client_name = client_profile.contact_person_name or job.client.full_name or "Unknown Client"
            client_address = f"{client_profile.business_address_street}, {client_profile.business_address_city}, {client_profile.business_address_state} {client_profile.business_address_zip}".strip(", ")
            client_business_name = f"({client_profile.business_name})" if client_profile.business_name else ""
            client_phone = client_profile.business_phone or job.client.phone_number or ""
        except Exception:
            client_name = job.client.full_name or "Unknown Client"
            client_address = job.location or ""
            client_business_name = ""
            client_phone = job.client.phone_number or ""

        # Format shift times
        start_str = job.shift_start.strftime("%I:%M %p").lstrip('0') if job.shift_start else ""
        end_str = job.shift_end.strftime("%I:%M %p").lstrip('0') if job.shift_end else ""
        shift_time = f"{start_str} - {end_str} ({job.shift_duration} hour{'s' if job.shift_duration != 1 else ''})"

        # Calculate Payment Breakdown
        subtotal = float(job.pay_rate) * float(job.shift_duration)
        service_fee = subtotal * 0.05
        tax_withholding = subtotal * 0.15
        total_earnings = subtotal - service_fee - tax_withholding

        # Check if the phlebotomist already applied
        from jobs.models import JobApplication
        app = JobApplication.objects.filter(job=job, phlebotomist=request.user).first()
        applied = app is not None
        application_status = app.status if applied else None

        data = {
            "success": True,
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "status": job.status,
            "applied": applied,
            "application_status": application_status,
            "client_name": client_name,
            "client_address": client_address,
            "client_business_name": client_business_name,
            "client_phone": client_phone,
            "shift_date": job.shift_date.strftime("%B %d, %Y") if job.shift_date else "",
            "shift_time": shift_time,
            "formatted_job_id": f"#{job.id}",
            "hourly_rate": f"${job.pay_rate:.2f}",
            "total_hours": f"{float(job.shift_duration):.1f} hrs",
            "subtotal": f"${subtotal:.2f}",
            "service_fee": f"-${service_fee:.2f}",
            "tax_withholding": f"-${tax_withholding:.2f}",
            "total_earnings": f"${total_earnings:.2f}",
            "client_info": {
                "name": client_name,
                "role": "Client",
                "address": client_address,
                "business_name": client_business_name,
                "phone": client_phone
            },
            "job_details": {
                "title": job.title,
                "shift_date": job.shift_date.strftime("%B %d, %Y") if job.shift_date else "",
                "shift_time": shift_time,
                "formatted_job_id": f"#{job.id}",
                "description": job.description
            },
            "payment_breakdown": {
                "hourly_rate": f"${job.pay_rate:.2f}",
                "total_hours": f"{float(job.shift_duration):.1f} hrs",
                "subtotal": f"${subtotal:.2f}",
                "service_fee": f"-${service_fee:.2f}",
                "tax_withholding": f"-${tax_withholding:.2f}",
                "total_earnings": f"${total_earnings:.2f}"
            }
        }
        return Response(data, status=status.HTTP_200_OK)

class PhlebotomistPendingJobListAPIView(NewAPIView):
    serializer_class = EmptySerializer
    permission_classes = [IsApprovedPhlebotomist]
    http_method_names = ['get']

    @swagger_auto_schema(tags=['App (Phlebotomist) - Home Section'])
    def get(self, request):
        """
        **Get Pending Jobs for Phlebotomist**\n
        Retrieve a list of jobs that are pending assignment to a phlebotomist.

        Example Response:
        ```json
        {
            "success": true,
            "data": [
                    {
                        "id": "JB-26-000002",
                        "title": "Massage Therapist",
                        "location": "123 Main St, Anytown, USA",
                        "shift_date": "August 14, 2025",
                        "shift_time": "10:00 AM - 6:00 PM",
                        "formatted_job_id": "#JB-26-000002",
                        "applied": false,
                        "accepted": false
                    },
                    {
                        "id": "JB-26-000003",
                        "title": "Yoga Instructor",
                        "location": "456 Oak Ave, Otherville, USA",
                        "shift_date": "August 15, 2025",
                        "shift_time": "9:00 AM - 5:00 PM",
                        "formatted_job_id": "#JB-26-000003",
                        "applied": false,
                        "accepted": false
                    }
                ],
            "message": "Pending jobs list retrieved successfully."
        }
        ```

        Error Responses:
        - 403 Forbidden: If the user is not authenticated or not an approved phlebotomist.
        """
        from jobs.models import Job, JobApplication, JobAssignment
        
        # Get all job assignments for the authenticated phlebotomist with PENDING status
        assignments = JobAssignment.objects.filter(
            phlebotomist=request.user,
            status=JobAssignment.PENDING
        ).select_related('job').order_by('job__shift_date')

        jobs_list = []
        for assignment in assignments:
            job = assignment.job
            
            # Check if phlebotomist already applied
            applied = JobApplication.objects.filter(job=job, phlebotomist=request.user).exists()
            accepted = assignment.signed_by_phlebotomist
            
            # Format shift times
            start_str = job.shift_start.strftime("%I:%M %p").lstrip('0') if job.shift_start else ""
            end_str = job.shift_end.strftime("%I:%M %p").lstrip('0') if job.shift_end else ""
            shift_time = f"{start_str} - {end_str}" if start_str and end_str else ""
            
            jobs_list.append({
                "id": job.id,
                "title": job.title,
                "location": job.location,
                "shift_date": job.shift_date.strftime("%B %d, %Y") if job.shift_date else "",
                "shift_time": shift_time,
                "formatted_job_id": f"#{job.id}",
                "applied": applied,
                "accepted": accepted
            })
        
        data = {
            "success": True,
            "data": jobs_list,
            "message": "Pending jobs list retrieved successfully."
        }
        return Response(data, status=status.HTTP_200_OK)

class PhlebotomistAcceptJobsAPIView(NewAPIView):
    permission_classes = [IsApprovedPhlebotomist]
    serializer_class = EmptySerializer
    http_method_names = ['patch']

    @swagger_auto_schema(
        request_body=EmptySerializer,
        tags=['App (Phlebotomist) - Home Section']
    )
    def patch(self, request, job_id):
        from jobs.models import Job, JobApplication, JobAssignment
        
        if not job_id:
            return Response({
                "success": False,
                "message": "Job ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get job assignment for the authenticated phlebotomist with PENDING status first
        try:
            assignment = JobAssignment.objects.get(
                phlebotomist=request.user,
                job_id=job_id,
                status=JobAssignment.PENDING
            )
        except JobAssignment.DoesNotExist:
            return Response({
                "success": False,
                "message": "Job assignment not found or already accepted."
            }, status=status.HTTP_404_NOT_FOUND)

        job = assignment.job
        if job.status in [Job.DRAFT, Job.PENDING_APPROVAL, Job.IN_PROGRESS, Job.COMPLETED, Job.CANCELLED]:
            return Response({
                "success": False,
                "message": "Job cannot be accepted as it is not Open or Approved."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Accept the job assignment
        assignment.signed_by_phlebotomist = True
        assignment.status = JobAssignment.ACTIVE
        assignment.save()

        job.status = Job.IN_PROGRESS
        job.save()
        
        data = {
            "success": True,
            "message": "Job accepted successfully."
        }
        return Response(data, status=status.HTTP_200_OK)

class UserRatingsReviewsAPIView(NewAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer
    http_method_names = ['get']

    def get(self, request):
        """
        **Get User Ratings and Reviews**\n

        Retrieve a list of ratings and reviews for the authenticated user.
        
        Example Response:
        ```json
        {
            "success": true,
            "data": {
                "average_rating": 4.0,
                "total_reviews_count": 1,
                "reviews": [
                    {
                        "id": 1,
                        "reviewer_name": "Phleb Reviewed",
                        "reviewer_profile_picture": "https://example.com/media/phlebotomist/profile_picture.jpg",
                        "rating": 4,
                        "comment": "Very nice client, on time.",
                        "created_at": "2 hours ago"
                    }
                ]
            },
            "message": "Ratings and reviews retrieved successfully."
        }
        ```

        Error Responses:
        - 401 Unauthorized: If the user is not authenticated.
        """
        from communication.models import Review
        from django.db.models import Avg
        from django.utils import timezone
        
        # Calculate humanized time
        def humanize_time(dt):
            now = timezone.now()
            diff = now - dt
            if diff.days == 0:
                if diff.seconds < 60:
                    return "just now"
                elif diff.seconds < 3600:
                    minutes = diff.seconds // 60
                    return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
                else:
                    hours = diff.seconds // 3600
                    return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif diff.days < 7:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} week{'s' if weeks != 1 else ''} ago"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months} month{'s' if months != 1 else ''} ago"
            else:
                years = diff.days // 365
                return f"{years} year{'s' if years != 1 else ''} ago"

        reviews = Review.objects.filter(reviewed=request.user).order_by('-created_at')
        total_reviews_count = reviews.count()
        
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        average_rating = round(avg_rating, 1) if avg_rating is not None else 0.0

        reviews_list = []
        for r in reviews:
            pic_url = request.build_absolute_uri(r.reviewer.profile_picture.url) if r.reviewer.profile_picture else None
            reviews_list.append({
                "id": r.id,
                "reviewer_name": r.reviewer.full_name,
                "reviewer_profile_picture": pic_url,
                "rating": r.rating,
                "comment": r.comment,
                "created_at": humanize_time(r.created_at)
            })

        data = {
            "success": True,
            "data": {
                "average_rating": average_rating,
                "total_reviews_count": total_reviews_count,
                "reviews": reviews_list
            },
            "message": "Ratings and reviews retrieved successfully."
        }
        return Response(data, status=status.HTTP_200_OK)

class ClientRatingsReviewsAPIView(UserRatingsReviewsAPIView):
    permission_classes = [IsApprovedClient]

    @swagger_auto_schema(tags=['App (Client) - Home Section'])
    def get(self, request, *args, **kwargs):
        """
        **Get Client Ratings and Reviews**\n

        Retrieve a list of ratings and reviews for the authenticated client user.
        
        Example Response:
        ```json
        {
            "success": true,
            "data": {
                "average_rating": 4.5,
                "total_reviews_count": 2,
                "reviews": [
                    {
                        "id": 2,
                        "reviewer_name": "John Doe",
                        "reviewer_profile_picture": "https://example.com/media/phlebotomist/profile.jpg",
                        "rating": 4,
                        "comment": "Good service.",
                        "created_at": "3 hours ago"
                    },
                    {
                        "id": 1,
                        "reviewer_name": "Jane Smith",
                        "reviewer_profile_picture": "https://example.com/media/phlebotomist/profile2.jpg",
                        "rating": 5,
                        "comment": "Excellent phlebotomist!",
                        "created_at": "5 hours ago"
                    }
                ]
            },
            "message": "Ratings and reviews retrieved successfully."
        }
        ```

        Error Responses:
        - 401 Unauthorized: If the user is not authenticated.
        """
        return super().get(request, *args, **kwargs)

class PhlebotomistRatingsReviewsAPIView(UserRatingsReviewsAPIView):
    permission_classes = [IsApprovedPhlebotomist]

    @swagger_auto_schema(tags=['App (Phlebotomist) - Home Section'])
    def get(self, request, *args, **kwargs):
        """
        **Get Phlebotomist Ratings and Reviews**\n

        Retrieve a list of ratings and reviews for the authenticated phlebotomist user.
        
        Example Response:
        ```json
        {
            "success": true,
            "data": {
                "average_rating": 4.5,
                "total_reviews_count": 2,
                "reviews": [
                    {
                        "id": 2,
                        "reviewer_name": "John Doe",
                        "reviewer_profile_picture": "https://example.com/media/client/profile.jpg",
                        "rating": 4,
                        "comment": "Good service.",
                        "created_at": "3 hours ago"
                    },
                    {
                        "id": 1,
                        "reviewer_name": "Jane Smith",
                        "reviewer_profile_picture": "https://example.com/media/client/profile2.jpg",
                        "rating": 5,
                        "comment": "Excellent client!",
                        "created_at": "5 hours ago"
                    }
                ]
            },
            "message": "Ratings and reviews retrieved successfully."
        }
        ```

        Error Responses:
        - 401 Unauthorized: If the user is not authenticated.
        """
        return super().get(request, *args, **kwargs)

class ReportUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    from jobs.serializers import ReportUserSerializer
    serializer_class = ReportUserSerializer
    http_method_names = ['get', 'post']

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('user_id', openapi.IN_QUERY, description="ID of the user to get details for", type=openapi.TYPE_INTEGER, required=True)
        ],
        tags=['App (Common) - Reporting']
    )
    def get(self, request, *args, **kwargs):
        """
        Get user details for the authenticated user.
        
        **Request Example**:
        ```json
        {
            "reported_user_id": 1,
            "reason": "inappropriate language",
            "additional_details": "This user said inappropriate things to me.",
            "job_id": 1
        }
        ```
        
        **Response Example**:
        ```json
        {
            "success": true,
            "data": {
                "id": 1,
                "full_name": "John Doe",
                "avatar": "https://example.com/media/user/profile.jpg",
                "rating": 4.5,
                "reviews_count": 2,
                "distance": "2.3 miles away",
                "subtitle": "Certified Phlebotomist"
            },
            "message": "User detail retrieved successfully."
        }
        ```
        
        Error Responses:
        - 401 Unauthorized: If the user is not authenticated.
        - 400 Bad Request: If user ID is missing or invalid.
        - 404 Not Found: If the user does not exist.
        """
        from authentication.models import User
        from communication.models import Review
        from django.db.models import Avg

        user_id = request.query_params.get('user_id') or request.query_params.get('reported_user_id')
        if not user_id:
            return Response({
                "success": False,
                "message": "User ID is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "message": "User does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        # Calculate rating
        reviews = Review.objects.filter(reviewed=user)
        avg = reviews.aggregate(Avg('rating'))['rating__avg']
        rating = round(avg, 1) if avg is not None else 5.0
        reviews_count = reviews.count()

        # Subtitle
        if user.role == 'phlebotomist':
            try:
                from authentication.models import Phlebotomist
                profile = Phlebotomist.objects.get(user=user)
                specialty = profile.get_specialty_display() if hasattr(profile, 'get_specialty_display') else (profile.specialty or "Certified Phlebotomist")
                exp = f"{profile.years_of_experience} years exp" if profile.years_of_experience else "No exp"
                subtitle = f"{specialty} • {exp}"
            except Exception:
                subtitle = "Certified Phlebotomist"
        else:
            try:
                from authentication.models import Client
                profile = Client.objects.get(client=user)
                business_name = profile.business_name or "Client"
                business_type = profile.get_business_type_display() if hasattr(profile, 'get_business_type_display') else (profile.business_type or "Healthcare")
                subtitle = f"{business_name} • {business_type}"
            except Exception:
                subtitle = "Client"

        avatar_url = request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None

        data = {
            "success": True,
            "data": {
                "id": user.id,
                "full_name": user.full_name,
                "avatar": avatar_url,
                "rating": rating,
                "reviews_count": reviews_count,
                "distance": "2.3 miles away",
                "subtitle": subtitle
            },
            "message": "User detail retrieved successfully."
        }
        return Response(data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=ReportUserSerializer,
        tags=['App (Common) - Reporting']
    )
    def post(self, request, *args, **kwargs):
        """
        Report a user.

        **Request body**"
        - reported_user_id: integer, required
        - reason: string, required
        - additional_details: string, optional
        - job_id: integer, optional
        
        **Request Example**:
        ```json
        {
            "reported_user_id": 1,
            "reason": "inappropriate language",
            "additional_details": "This user said inappropriate things to me.",
            "job_id": 1
        }
        ```
        
        **Response Example**:
        ```json
        {
            "success": true,
            "data": {
                "id": 1,
                "reporter_id": 1,
                "reported_user_id": 2,
                "job_id": 3,
                "reason": "inappropriate_language",
                "additional_details": "This user said inappropriate things to me.",
                "status": "pending"
            },
            "message": "Report submitted successfully."
        }
        ```
        
        Error Responses:
        - 401 Unauthorized: If the user is not authenticated.
        - 400 Bad Request: If user ID is missing or invalid.
        - 404 Not Found: If the user does not exist.
        """
        from communication.models import Report
        from authentication.models import User
        from jobs.models import Job
        from jobs.serializers import ReportUserSerializer

        serializer = ReportUserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Validation failed.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        reported_user_id = serializer.validated_data.get('reported_user_id')
        reason = serializer.validated_data.get('reason')
        additional_details = serializer.validated_data.get('additional_details', '')
        job_id = serializer.validated_data.get('job_id')
        # Normalize reason to match REASON_CHOICES keys
        reason_map = {
            'inappropriate language': Report.INAPPROPRIATE_LANGUAGE,
            'harassment': Report.HARASSMENT,
            'spam': Report.SPAM,
            'fake profile': Report.FAKE_PROFILE,
            'other': Report.OTHER,
            'inappropriate_language': Report.INAPPROPRIATE_LANGUAGE,
            'fake_profile': Report.FAKE_PROFILE
        }
        normalized_reason = reason_map.get(reason.lower().strip(), reason)

        # Validate reason
        valid_reasons = [choice[0] for choice in Report.REASON_CHOICES]
        if normalized_reason not in valid_reasons:
            return Response({
                "success": False,
                "message": f"Invalid reason. Choose from: {', '.join(valid_reasons)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            reported_user = User.objects.get(id=reported_user_id)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "message": "Reported user does not exist."
            }, status=status.HTTP_404_NOT_FOUND)

        if reported_user == request.user:
            return Response({
                "success": False,
                "message": "You cannot report yourself."
            }, status=status.HTTP_400_BAD_REQUEST)

        job = None
        if job_id:
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "Job does not exist."
                }, status=status.HTTP_404_NOT_FOUND)

        report = Report.objects.create(
            reporter=request.user,
            reported_user=reported_user,
            job=job,
            reason=normalized_reason,
            additional_details=additional_details,
            status=Report.PENDING
        )

        return Response({
            "success": True,
            "message": "Report submitted successfully.",
            "data": {
                "id": report.id,
                "reporter_id": report.reporter.id,
                "reported_user_id": report.reported_user.id,
                "job_id": report.job.id if report.job else None,
                "reason": report.reason,
                "additional_details": report.additional_details,
                "status": report.status
            }
        }, status=status.HTTP_201_CREATED)

class PhlebotomistHomeAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer
    http_method_names = ['get']

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('date_filter', openapi.IN_QUERY, description="Filter metrics by: today, weekly, monthly, all", type=openapi.TYPE_STRING, required=False)
        ],
        tags=['App (Phlebotomist) - Home Section']
    )
    def get(self, request, *args, **kwargs):
        from authentication.models import User, Phlebotomist
        from communication.models import Review
        from jobs.models import Job, JobAssignment
        from django.db.models import Avg
        from django.utils import timezone
        import datetime

        try:
            user = User.objects.get(id=request.user.id)
            profile = Phlebotomist.objects.get(user=user)
        except User.DoesNotExist:
            return Response({
                "success": False,
                "message": "User does not exist."
            }, status=status.HTTP_404_NOT_FOUND)
        except Phlebotomist.DoesNotExist:
            return Response({
                "success": False,
                "message": "Phlebotomist profile not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # Calculate user rating
        reviews = Review.objects.filter(reviewed=user)
        avg = reviews.aggregate(Avg('rating'))['rating__avg']
        rating = round(avg, 1) if avg is not None else 4.8
        reviews_count = reviews.count()

        # Specialty & subtitle
        try:
            specialty = profile.get_specialty_display() if hasattr(profile, 'get_specialty_display') else (profile.specialty or "Certified Phlebotomist")
            exp = f"{profile.years_of_experience} years exp" if profile.years_of_experience else "No exp"
            subtitle = f"{specialty} • {exp}"
        except Exception:
            subtitle = "Certified Phlebotomist"

        avatar_url = request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None

        user_data = {
            "id": user.id,
            "full_name": user.full_name,
            "avatar": avatar_url,
            "rating": rating,
            "reviews_count": reviews_count,
            "subtitle": subtitle
        }

        # Date Filtering & Metrics
        date_filter = request.query_params.get('date_filter', 'all').lower()
        today_date = timezone.now().date()
        
        completed_assignments = JobAssignment.objects.filter(
            phlebotomist=user,
            status=JobAssignment.COMPLETED
        )
        
        metric_assignments = completed_assignments
        if date_filter == 'today':
            metric_assignments = metric_assignments.filter(job__shift_date=today_date)
        elif date_filter == 'weekly':
            start_week = today_date - datetime.timedelta(days=today_date.weekday())
            metric_assignments = metric_assignments.filter(job__shift_date__gte=start_week)
        elif date_filter == 'monthly':
            metric_assignments = metric_assignments.filter(
                job__shift_date__month=today_date.month,
                job__shift_date__year=today_date.year
            )

        # Total Earnings (80% net of subtotal)
        total_earnings = 0.0
        for assignment in metric_assignments:
            subtotal = float(assignment.job.pay_rate or 0) * float(assignment.job.shift_duration or 0)
            total_earnings += 0.80 * subtotal

        # Today Earnings
        today_assignments = completed_assignments.filter(job__shift_date=today_date)
        today_earnings = 0.0
        for assignment in today_assignments:
            subtotal = float(assignment.job.pay_rate or 0) * float(assignment.job.shift_duration or 0)
            today_earnings += 0.80 * subtotal

        # Pending Payouts (Active assignments earnings)
        active_assignments = JobAssignment.objects.filter(
            phlebotomist=user,
            status=JobAssignment.ACTIVE
        )
        pending_payouts = 0.0
        for assignment in active_assignments:
            subtotal = float(assignment.job.pay_rate or 0) * float(assignment.job.shift_duration or 0)
            pending_payouts += 0.80 * subtotal

        metrics = {
            "total_earnings": f"${total_earnings:,.0f}",
            "jobs_done": metric_assignments.count(),
            "rating": rating,
            "today_earnings": f"${today_earnings:,.0f}",
            "pending_payouts": f"${pending_payouts:,.0f}"
        }

        # Next Job Card
        now = timezone.now()
        next_assignment = JobAssignment.objects.filter(
            phlebotomist=user,
            status__in=[JobAssignment.ACTIVE, JobAssignment.PENDING]
        ).filter(
            job__shift_date__gte=today_date
        ).select_related('job', 'job__client').order_by('job__shift_date', 'job__shift_start').first()

        next_job_data = None
        if next_assignment:
            job = next_assignment.job
            date_str = "Today" if job.shift_date == today_date else job.shift_date.strftime("%B %d, %Y")
            start_str = job.shift_start.strftime("%I:%M %p").lstrip('0')
            end_str = job.shift_end.strftime("%I:%M %p").lstrip('0')
            shift_time_str = f"{date_str}, {start_str} - {end_str}"
            
            job_start_datetime = timezone.make_aware(datetime.datetime.combine(job.shift_date, job.shift_start))
            time_diff = job_start_datetime - now
            
            if time_diff.total_seconds() < 0:
                tag = "Started"
            else:
                hours = int(time_diff.total_seconds() // 3600)
                minutes = int((time_diff.total_seconds() % 3600) // 60)
                if hours > 0:
                    tag = f"In {hours} hour{'s' if hours != 1 else ''}"
                else:
                    tag = f"In {minutes} minute{'s' if minutes != 1 else ''}"
                    
            next_job_data = {
                "id": job.id,
                "title": job.title,
                "location": job.location,
                "shift_time": shift_time_str,
                "tag": tag,
                "client_name": job.client.full_name if job.client else "Client"
            }

        # License Expiration Countdown
        license_expiration = None
        if hasattr(profile, 'license_expiry_date') and profile.license_expiry_date:
            expiry_date = profile.license_expiry_date
            formatted_expiry = expiry_date.strftime("%d %B %Y")
            
            diff_days = (expiry_date - today_date).days
            if diff_days < 0:
                left_str = "Expired"
            else:
                years = diff_days // 365
                rem_days = diff_days % 365
                months = rem_days // 30
                days = rem_days % 30
                
                parts = []
                if years > 0:
                    parts.append(f"{years} Year{'s' if years != 1 else ''}")
                if months > 0:
                    parts.append(f"{months} Month{'s' if months != 1 else ''}")
                if days > 0:
                    parts.append(f"{days} Day{'s' if days != 1 else ''}")
                left_str = " ".join(parts) + " left" if parts else "Expires today"
                
            license_expiration = {
                "expiry_date": formatted_expiry,
                "days_left_text": left_str
            }

        # Recent Activity Stream
        recent_activities = []
        
        # 1. Job Assignment activities
        all_assignments = JobAssignment.objects.filter(phlebotomist=user).select_related('job').order_by('-created_at')[:5]
        for assign in all_assignments:
            job = assign.job
            subtotal = float(job.pay_rate or 0) * float(job.shift_duration or 0)
            net = 0.80 * subtotal
            
            if assign.status == JobAssignment.COMPLETED:
                title = "Job Completed"
                desc = job.location or ""
                amount = f"+${net:,.0f}"
            elif assign.status == JobAssignment.ACTIVE:
                title = "Job Accepted"
                desc = job.location or ""
                amount = f"+${net:,.0f}"
            else:
                title = "Job Offered"
                desc = job.location or ""
                amount = ""
                
            recent_activities.append({
                "title": title,
                "description": desc,
                "amount": amount,
                "type": "job",
                "date": assign.created_at
            })
            
        # 2. Review activities
        all_reviews = Review.objects.filter(reviewed=user).select_related('reviewer').order_by('-created_at')[:5]
        for rev in all_reviews:
            recent_activities.append({
                "title": f"New {rev.rating}-Star Rating",
                "description": f"From client {rev.reviewer.full_name}",
                "amount": "",
                "type": "rating",
                "date": rev.created_at
            })
            
        # Sort combined activity lists by date descending, keep top 5
        recent_activities.sort(key=lambda x: x['date'], reverse=True)
        recent_activities = recent_activities[:5]
        
        # Remove date key before serialization
        for act in recent_activities:
            act.pop('date')

        return Response({
            "success": True,
            "data": {
                "user": user_data,
                "metrics": metrics,
                "next_job": next_job_data,
                "license_expiration": license_expiration,
                "recent_activities": recent_activities
            },
            "message": "Phlebotomist home data retrieved successfully."
        }, status=status.HTTP_200_OK)



