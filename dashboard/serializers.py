from rest_framework import serializers
from authentication.models import Client, ClientDocument, Phlebotomist, Phlebotomist_document
from django.contrib.auth import get_user_model

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


