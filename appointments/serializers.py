from rest_framework import serializers
from appointments.models import ServicePackage, ServicePackageFeature, PatientProfile, Appointment, Payment
from authentication.serializers import UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class AppointmentCreateSerializer(serializers.Serializer):
    LOCATION_CHOICES = [
        ('home', 'Patient Home'),
        ('hospital', 'Hospital/Clinic'),
        ('lab', 'Lab'),
    ]
    MEDICAL_CHOICES = [
        ('Diabetes', 'Diabetes'),
        ('High Blood Pressure', 'High Blood Pressure'),
        ('Low Blood Pressure', 'Low Blood Pressure'),
        ('Thyroid', 'Thyroid'),
        ('Heart Disease', 'Heart Disease'),
        ('No Medical Conditions', 'No Medical Conditions'),
    ]
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    phone_number = serializers.CharField(write_only=True)
    dob = serializers.DateField(write_only=True)
    gender = serializers.ChoiceField(choices=[('male', 'Male'), ('female', 'Female')], write_only=True)
    service_package = serializers.PrimaryKeyRelatedField(queryset=ServicePackage.objects.all(), write_only=True)
    appointment_date = serializers.DateField(write_only=True)
    start_time = serializers.TimeField(write_only=True)
    end_time = serializers.TimeField(write_only=True)
    location_type = serializers.ChoiceField(choices=LOCATION_CHOICES, write_only=True)
    location = serializers.CharField(write_only=True)
    current_medications = serializers.CharField(write_only=True)
    prescription = serializers.FileField(write_only=True)
    known_allergies = serializers.CharField(write_only=True)
    medical_conditions = serializers.ChoiceField(choices=MEDICAL_CHOICES, write_only=True, allow_null=True, allow_blank=True)
    special_requests = serializers.CharField(write_only=True)
    email_result_notification = serializers.BooleanField(write_only=True)
    sms_appointment_reminders = serializers.BooleanField(write_only=True)


class ServicePackageFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicePackageFeature
        fields = ['id', 'name']


class ServicePackageListSerializer(serializers.ModelSerializer):
    features = ServicePackageFeatureSerializer(many=True, read_only=True)

    class Meta:
        model = ServicePackage
        fields = ['id', 'icon', 'name', 'description', 'price', 'is_active', 'features', 'created_at', 'updated_at']


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number', 'dob', 'gender', 'created_at', 'updated_at']

class AppointmentListSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    service_package = ServicePackageListSerializer(read_only=True)
    phlebotomist = UserSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'service_package', 'phlebotomist', 
            'appointment_date', 'start_time', 'end_time', 
            'location_type', 'location', 'status', 'created_at'
        ]


class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer(read_only=True)
    service_package = ServicePackageListSerializer(read_only=True)
    phlebotomist = UserSerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'service_package', 'phlebotomist', 
            'appointment_date', 'start_time', 'end_time', 
            'location_type', 'location', 'current_medications', 
            'prescription', 'known_allergies', 'medical_conditions', 
            'special_requests', 'email_result_notification', 
            'sms_appointment_reminders', 'status', 'created_at', 'updated_at'
        ]


class AppointmentUserIdSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


from appointments.models import Wallet, WalletTransaction, PayoutRequest

class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ['id', 'transaction_type', 'amount', 'platform_fee', 'description', 'created_at']

class WalletBalanceSerializer(serializers.ModelSerializer):
    transactions = WalletTransactionSerializer(many=True, read_only=True)
    total_platform_charge = serializers.DecimalField(source='total_platform_fees', max_digits=12, decimal_places=2, read_only=True)
    withdrawable_amount = serializers.DecimalField(source='balance', max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Wallet
        fields = ['balance', 'total_earned', 'total_platform_charge', 'withdrawable_amount', 'transactions']

class PayoutRequestCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)

class PatientListSerializer(serializers.Serializer):
    appointment_id = serializers.IntegerField(source='id')
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()

    def get_patient_name(self, obj):
        if obj.patient:
            return f"{obj.patient.first_name} {obj.patient.last_name}".strip()
        return "Unknown Patient"

    def get_patient_id(self, obj):
        if obj.patient:
            year = obj.patient.created_at.year if obj.patient.created_at else 2025
            return f"SID-{year}-{obj.patient.id:03d}"
        return "N/A"


class PatientAppointmentDetailSerializer(serializers.Serializer):
    patient_info = serializers.SerializerMethodField()
    medical_info = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    client_info = serializers.SerializerMethodField()
    service_details = serializers.SerializerMethodField()
    service_overview = serializers.SerializerMethodField()

    def get_patient_info(self, obj):
        patient = obj.patient
        if not patient:
            return {}
        
        age_str = "N/A"
        if patient.dob:
            from datetime import date
            today = date.today()
            age = today.year - patient.dob.year - ((today.month, today.day) < (patient.dob.month, patient.dob.day))
            age_str = f"{age} years"

        date_str = obj.appointment_date.strftime("%b %d, %Y") if obj.appointment_date else "N/A"
        time_str = obj.start_time.strftime("%I:%M %p") if obj.start_time else "N/A"
        year = patient.created_at.year if patient.created_at else 2025

        return {
            "name": f"{patient.first_name} {patient.last_name}".strip(),
            "patient_id": f"SID-{year}-{patient.id:03d}",
            "age": age_str,
            "phone": patient.phone_number or "N/A",
            "date": date_str,
            "time": time_str
        }

    def get_medical_info(self, obj):
        prescription_url = None
        prescription_name = None
        prescription_uploaded_at = None
        
        request = self.context.get('request')
        if obj.prescription:
            import os
            prescription_name = os.path.basename(obj.prescription.name)
            if request:
                prescription_url = request.build_absolute_uri(obj.prescription.url)
            else:
                prescription_url = obj.prescription.url
            
            from django.utils import timezone
            now = timezone.now()
            diff = now - obj.updated_at
            if diff.days > 0:
                if diff.days == 1:
                    prescription_uploaded_at = "Uploaded yesterday"
                else:
                    prescription_uploaded_at = f"Uploaded {diff.days} days ago"
            else:
                hours = diff.seconds // 3600
                if hours > 0:
                    prescription_uploaded_at = f"Uploaded {hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    minutes = diff.seconds // 60
                    if minutes > 0:
                        prescription_uploaded_at = f"Uploaded {minutes} minute{'s' if minutes > 1 else ''} ago"
                    else:
                        prescription_uploaded_at = "Uploaded just now"

        return {
            "prescription_url": prescription_url,
            "prescription_name": prescription_name,
            "prescription_uploaded_at": prescription_uploaded_at,
            "special_instructions": obj.special_requests or "No special instructions."
        }

    def get_location(self, obj):
        loc_type_map = {
            'home': "Patient's Home",
            'hospital': "Hospital/Clinic",
            'lab': "Lab"
        }
        return {
            "type": loc_type_map.get(obj.location_type, "Patient's Home"),
            "address": obj.location or "N/A"
        }

    def get_client_info(self, obj):
        client = obj.client
        if not client:
            return {}
        
        client_profile = getattr(client, 'client_profile', None)
        
        from communication.models import Review
        from django.db.models import Avg, Count
        reviews_summary = Review.objects.filter(reviewed=client).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )
        avg_rating = reviews_summary.get('avg_rating') or 4.8
        total_reviews = reviews_summary.get('total_reviews') or 127
        
        member_since = client.created_at.year if client.created_at else 2020
        
        if client_profile:
            business_name = client_profile.business_name
            business_type = client_profile.get_business_type_display() if hasattr(client_profile, 'get_business_type_display') else client_profile.business_type
            employees = f"{client_profile.no_of_employees}+ employees" if client_profile.no_of_employees else "250+ employees"
        else:
            business_name = client.full_name
            business_type = "Healthcare"
            employees = "250+ employees"
            
        request = self.context.get('request')
        profile_picture_url = None
        if client.profile_picture:
            if request:
                profile_picture_url = request.build_absolute_uri(client.profile_picture.url)
            else:
                profile_picture_url = client.profile_picture.url
                
        return {
            "business_name": business_name,
            "business_type": business_type,
            "profile_picture": profile_picture_url,
            "rating": round(float(avg_rating), 1),
            "reviews_count": total_reviews,
            "no_of_employees": employees,
            "member_since": member_since
        }

    def get_service_details(self, obj):
        pkg = obj.service_package
        if not pkg:
            return {}
            
        features_list = [f.name for f in pkg.features.all()]
        features_str = ", ".join(features_list) if features_list else pkg.description
        
        duration_str = "30 minutes"
        if obj.start_time and obj.end_time:
            from datetime import datetime, date
            dt1 = datetime.combine(date.today(), obj.start_time)
            dt2 = datetime.combine(date.today(), obj.end_time)
            diff = dt2 - dt1
            minutes = int(diff.total_seconds() / 60)
            if minutes > 0:
                duration_str = f"{minutes} minutes"

        return {
            "name": pkg.name,
            "features": features_str,
            "duration": f"Estimated duration: {duration_str}"
        }

    def get_service_overview(self, obj):
        loc_type_map = {
            'home': "Mobile Blood Draw",
            'hospital': "In-Clinic Phlebotomy",
            'lab': "Laboratory Testing"
        }
        service_name = loc_type_map.get(obj.location_type, "Mobile Blood Draw")
        date_str = obj.appointment_date.strftime("%B %d, %Y") if obj.appointment_date else "N/A"
        time_str = obj.start_time.strftime("%I:%M %p") if obj.start_time else "N/A"
        
        pkg = obj.service_package
        total_amount = f"${pkg.price}" if pkg else "$0.00"

        return {
            "service": service_name,
            "date": date_str,
            "time": time_str,
            "total_amount": total_amount
        }

