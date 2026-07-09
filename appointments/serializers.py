from rest_framework import serializers
from appointments.models import ServicePackage, ServicePackageFeature, PatientProfile, Appointment, Payment
from authentication.serializers import UserSerializer

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


class AppointmentCreateSerializer(serializers.ModelSerializer):
    patient = PatientProfileSerializer()

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
        read_only_fields = ['status']

    def create(self, validated_data):
        patient_data = validated_data.pop('patient')
        patient = PatientProfile.objects.create(**patient_data)
        appointment = Appointment.objects.create(patient=patient, **validated_data)
        return appointment


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
