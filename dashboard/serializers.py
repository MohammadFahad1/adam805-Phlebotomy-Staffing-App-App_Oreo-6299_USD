from rest_framework import serializers
from authentication.models import Client, ClientDocument, Phlebotomist, Phlebotomist_document
from django.contrib.auth import get_user_model
from jobs.models import Job

User = get_user_model()

class DashboardHomeSerializer(serializers.Serializer):
    total_users = serializers.SerializerMethodField()
    pending_verifications = serializers.SerializerMethodField()
    active_jobs = serializers.SerializerMethodField()
    revenue_this_month = serializers.SerializerMethodField()
    pending_registrations_count = serializers.SerializerMethodField()
    document_to_verify_count = serializers.SerializerMethodField()
    recent_activities = serializers.SerializerMethodField()
    jobs_completed_today = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    active_disputes = serializers.SerializerMethodField()
    response_time = serializers.SerializerMethodField()

    def get_total_users(self, obj):
        return f"{User.objects.count():.2f}"
    
    def get_pending_verifications(self, obj):
        return f"{0}"
    
    def get_active_jobs(self, obj):
        return f"{0}"
    
    def get_revenue_this_month(self, obj):
        return f"{0:.2f}"
    
    def get_pending_registrations_count(self, obj):
        unapproved_clients = Client.objects.filter(is_approved=False).count()
        unapproved_phlebotomists = Phlebotomist.objects.filter(approved=False).count()
        return f"{unapproved_clients + unapproved_phlebotomists:.2f}"
    
    def get_document_to_verify_count(self, obj):
        unapproved_documents_phlebotomist = Phlebotomist_document.objects.filter(approved=False).count()
        unapproved_documents_client = ClientDocument.objects.filter(approved=False).count()
        unapproved_documents = unapproved_documents_phlebotomist + unapproved_documents_client
        if unapproved_documents > 0:
            return f"{unapproved_documents:.2f}"
        return f"{0}"
    
    def get_recent_activities(self, obj):
        return [
            {
                "id": 1,
                "activity": "New User Registration",
                "user": "John Doe",
                "timestamp": "Just Now"
            },
            {
                "id": 2,
                "activity": "Job Posting Created",
                "user": "Memorial Hospital",
                "timestamp": "15 minutes ago"
            },
            {
                "id": 3,
                "activity": "Dispute reported",
                "user": "Job #1234",
                "timestamp": "1 hour ago"
            }
        ]
    
    def get_jobs_completed_today(self, obj):
        return f"{47}"
    
    def get_average_rating(self, obj):
        return f"{4.8:.1f}"
    
    def get_active_disputes(self, obj):
        return f"{3}"
    
    def get_response_time(self, obj):
        return f"{2.3:.1f}"

class BooleanSerializer(serializers.Serializer):
    approve = serializers.BooleanField(required=True)

class JobStatusChoicesSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Job.STATUS_CHOICES, required=True)

class UserIdSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)

# ── Nested helpers ────────────────────────────────────────────────────────────

class AvailabilitySlotSerializer(serializers.Serializer):
    class Meta:
        ref_name = 'DashboardAvailabilitySlot'

    day        = serializers.CharField(help_text="Day name, e.g. 'Monday'.")
    date       = serializers.DateField(help_text="Date in YYYY-MM-DD format.")
    start_time = serializers.TimeField(help_text="Start time in HH:MM format.")
    end_time   = serializers.TimeField(help_text="End time in HH:MM format.")
    is_available = serializers.BooleanField(default=True, required=False)


# ── Phlebotomist edit serializer ──────────────────────────────────────────────

class PhlebotomistProfileEditSerializer(serializers.Serializer):
    """All fields are optional — only send what you want to change."""

    # User fields
    full_name       = serializers.CharField(required=False, help_text="Full legal name.")
    email           = serializers.EmailField(required=False, help_text="Unique email address.")
    phone_number    = serializers.CharField(required=False, help_text="Contact phone number.")
    gender          = serializers.ChoiceField(choices=[('male', 'Male'), ('female', 'Female')], required=False)
    dob             = serializers.DateField(required=False, help_text="Date of birth in YYYY-MM-DD format.")
    profile_picture = serializers.ImageField(required=False, allow_null=True, help_text="Profile picture image file.")

    # Phlebotomist profile fields
    license_number      = serializers.CharField(required=False)
    license_expiry_date = serializers.DateField(required=False, help_text="YYYY-MM-DD.")
    years_of_experience = serializers.IntegerField(required=False, min_value=0)
    specialty = serializers.ChoiceField(
        choices=[
            ('general_phlebotomy',      'General Phlebotomy'),
            ('iv_insertion_or_therapy', 'IV Insertion/Therapy'),
            ('oncology_or_chemotherapy','Oncology/Chemotherapy'),
            ('medical_nurse',           'Medical Nurse'),
        ],
        required=False,
    )
    work_preference = serializers.ChoiceField(
        choices=[('part_time', 'Part-time'), ('full_time', 'Full-time')],
        required=False,
    )
    service_area = serializers.CharField(required=False)
    address      = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Nested — full replace when provided
    skills         = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text='List of skill names. Replaces all existing skills, e.g. ["venipuncture", "iv_insertion"].',
    )
    availabilities = AvailabilitySlotSerializer(
        many=True,
        required=False,
        help_text="List of availability slots. Replaces all existing slots.",
    )


# ── Client edit serializer ────────────────────────────────────────────────────

class ClientProfileEditSerializer(serializers.Serializer):
    """All fields are optional — only send what you want to change."""

    # User fields
    full_name       = serializers.CharField(required=False, help_text="Full legal name.")
    email           = serializers.EmailField(required=False, help_text="Unique email address.")
    phone_number    = serializers.CharField(required=False)
    gender          = serializers.ChoiceField(choices=[('male', 'Male'), ('female', 'Female')], required=False)
    dob             = serializers.DateField(required=False, help_text="Date of birth in YYYY-MM-DD format.")
    profile_picture = serializers.ImageField(required=False, allow_null=True, help_text="Profile picture image file.")

    # Client profile fields
    business_name           = serializers.CharField(required=False)
    business_type           = serializers.ChoiceField(
        choices=[('healthcare', 'Healthcare'), ('individual', 'Individual')],
        required=False,
    )
    business_address_street = serializers.CharField(required=False)
    business_address_city   = serializers.CharField(required=False)
    business_address_state  = serializers.CharField(required=False)
    business_address_zip    = serializers.CharField(required=False)
    contact_person_name     = serializers.CharField(required=False)
    business_phone          = serializers.CharField(required=False)
    business_license_number = serializers.CharField(required=False)
    business_description    = serializers.CharField(required=False, style={'base_template': 'textarea.html'})
    hourly_pay_rate         = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    preferred_job_type      = serializers.ChoiceField(
        choices=[
            ('in_clinic_phlebotomy', 'In-Clinic Phlebotomy'),
            ('mobile_blood_draw',    'Mobile Blood Draw'),
            ('laboratory_testing',   'Laboratory Testing'),
        ],
        required=False,
    )
    work_preference  = serializers.ChoiceField(
        choices=[('part_time', 'Part-time'), ('full_time', 'Full-time')],
        required=False,
    )
    no_of_employees = serializers.IntegerField(required=False, min_value=0)
    signature       = serializers.ImageField(required=False, allow_null=True, help_text="Signature image file.")

    # Nested — full replace when provided
    availabilities = AvailabilitySlotSerializer(
        many=True,
        required=False,
        help_text="List of availability slots. Replaces all existing slots.",
    )


class ReportListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    reported_by = serializers.SerializerMethodField()
    case_id = serializers.SerializerMethodField()
    time_elapsed = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        from communication.models import Report
        model = Report
        fields = [
            'id',
            'title',
            'reported_by',
            'case_id',
            'time_elapsed',
            'priority',
            'status',
            'status_display',
            'reason',
            'additional_details',
            'created_at'
        ]

    def get_title(self, obj):
        mapping = {
            'inappropriate_language': 'Inappropriate Message',
            'harassment': 'Harassment Report',
            'spam': 'Spam Report',
            'fake_profile': 'Fake Profile Report',
            'other': 'Payment Issue'
        }
        return mapping.get(obj.reason, 'Payment Issue')

    def get_reported_by(self, obj):
        if obj.reporter:
            return obj.reporter.full_name or obj.reporter.email
        return 'Unknown'

    def get_case_id(self, obj):
        prefix_mapping = {
            'inappropriate_language': 'IM',
            'harassment': 'HR',
        }
        prefix = prefix_mapping.get(obj.reason, 'DS')
        year = obj.created_at.year if obj.created_at else 2024
        obj_id = obj.id or 1
        return f"#{prefix}-{year}-{obj_id:03d}"

    def get_time_elapsed(self, obj):
        if not obj.created_at:
            return "Just now"
        from django.utils import timezone
        now = timezone.now()
        diff = now - obj.created_at
        if diff.days > 0:
            if diff.days == 1:
                return "1 day ago"
            return f"{diff.days} days ago"
        hours = diff.seconds // 3600
        if hours > 0:
            if hours == 1:
                return "1 hour ago"
            return f"{hours} hours ago"
        minutes = (diff.seconds % 3600) // 60
        if minutes > 0:
            if minutes == 1:
                return "1 minute ago"
            return f"{minutes} minutes ago"
        return "Just now"

    def get_priority(self, obj):
        priority_mapping = {
            'harassment': 'High',
            'inappropriate_language': 'Medium',
            'spam': 'Low',
            'fake_profile': 'Medium',
            'other': 'High'
        }
        return priority_mapping.get(obj.reason, 'High')

    def get_status_display(self, obj):
        if obj.status == 'resolved':
            return 'Solved'
        elif obj.status == 'reviewed':
            return 'Under Review'
        else:
            return 'Pending'
