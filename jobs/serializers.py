from rest_framework import serializers
from jobs.models import Job


class JobCreateSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=255,
        help_text="Job title, e.g. 'Phlebotomist Needed'."
    )
    professional_type = serializers.ChoiceField(
        choices=Job.PROFESSIONAL_TYPE_CHOICES,
        help_text="Type of professional required. Choices: RN, LPN, CP."
    )
    description = serializers.CharField(
        style={'base_template': 'textarea.html'},
        help_text="Describe the required tasks, responsibilities, and any specific requirements."
    )
    location = serializers.CharField(
        max_length=255,
        help_text="Full address or clinic location."
    )
    city = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="City where the job is located (optional)."
    )
    shift_date = serializers.DateField(
        help_text="Date of the shift in YYYY-MM-DD format."
    )
    shift_start = serializers.TimeField(
        help_text="Shift start time in HH:MM (24-hour) format."
    )
    shift_end = serializers.TimeField(
        help_text="Shift end time in HH:MM (24-hour) format."
    )
    shift_duration = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=0,
        help_text="Estimated shift duration in hours. Auto-calculated from shift_start/shift_end if omitted."
    )
    pay_type = serializers.ChoiceField(
        choices=Job.PAY_TYPE_CHOICES,
        help_text="Payment structure. Choices: hourly, flat_rate."
    )
    pay_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Compensation amount, e.g. 30.00."
    )
    job_type = serializers.ChoiceField(
        choices=Job.JOB_TYPE_CHOICES,
        help_text="Type of job. Choices: urgent, full_day, part_time."
    )


class ReportUserSerializer(serializers.Serializer):
    reported_user_id = serializers.IntegerField(
        required=True,
        help_text="ID of the user being reported."
    )
    reason = serializers.CharField(
        max_length=255,
        required=True,
        help_text="Reason for reporting. E.g. 'Inappropriate Language', 'Harassment', 'Spam', 'Fake Profile', 'Other'"
    )
    additional_details = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Optional additional details about the report."
    )
    job_id = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Optional associated Job ID."
    )



