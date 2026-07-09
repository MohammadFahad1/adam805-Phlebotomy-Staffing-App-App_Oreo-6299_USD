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
    phlebotomist = serializers.PrimaryKeyRelatedField(read_only=True)
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
