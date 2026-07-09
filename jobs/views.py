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


