from rest_framework import serializers
from authentication.models import Phlebotomist, Client
from django.contrib.auth import get_user_model

User = get_user_model()

class DashboardHomeSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    pending_verifications = serializers.IntegerField()
    active_jobs = serializers.IntegerField()
    revenue_this_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_registrations_count = serializers.IntegerField()
    document_to_verify_count = serializers.IntegerField()
    recent_activities = serializers.SerializerMethodField()
    jobs_completed_today = serializers.IntegerField()
    average_rating = serializers.DecimalField(max_digits=10, decimal_places=2)
    active_disputes = serializers.IntegerField()
    response_time = serializers.DecimalField(max_digits=10, decimal_places=2)