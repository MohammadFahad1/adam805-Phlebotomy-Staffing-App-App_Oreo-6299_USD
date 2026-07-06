from rest_framework import serializers
from authentication import models

class PhlebotomistAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PhlebotomistAvailability
        fields = ['id', 'day', 'date', 'start_time', 'end_time', 'is_available']

class PhlebotomistDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Phlebotomist_document
        fields = ['id', 'document_name', 'document_file', 'approved']
        read_only_fields = ['approved']

class PhlebotomistSerializer(serializers.ModelSerializer):
    availabilities = PhlebotomistAvailabilitySerializer(many=True, read_only=True)
    skills = serializers.SlugRelatedField(many=True, read_only=True, slug_field='skill_name')
    documents = PhlebotomistDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = models.Phlebotomist
        fields = [
            'id',
            'license_number',
            'license_expiry_date',
            'years_of_experience',
            'specialty',
            'work_preference',
            'service_area',
            'address',
            'approved',
            'availabilities',
            'skills',
            'documents',
            'created_at',
            'updated_at'
        ]

class UserSerializer(serializers.ModelSerializer):
    phlebotomist_profile = PhlebotomistSerializer(read_only=True)

    class Meta:
        model = models.User
        fields = [
            'id',
            'full_name',
            'email',
            'phone_number',
            'gender',
            'dob',
            'role',
            'profile_picture',
            'phlebotomist_profile',
            'created_at',
            'updated_at'
        ]

class PhlebotomistRegistrationSerializer(serializers.Serializer):
    # User fields
    full_name = serializers.CharField()
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField()
    gender = serializers.ChoiceField(choices=models.User.GENDER_CHOICES)
    dob = serializers.DateField()
    role = serializers.ChoiceField(choices=models.User.ROLE_CHOICES, default=models.User.PHLEBOTOMIST, read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    # Phlebotomist profile fields
    license_number = serializers.CharField()
    license_expiry_date = serializers.DateField()
    years_of_experience = serializers.IntegerField(default=0, min_value=0)
    specialty = serializers.ChoiceField(choices=models.Phlebotomist.SPECIALTY_CHOICES)
    work_preference = serializers.ChoiceField(choices=models.Phlebotomist.WORK_PREFERENCE_CHOICES)
    service_area = serializers.CharField()
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    # Nested fields
    availabilities = PhlebotomistAvailabilitySerializer(many=True, required=True)
    skills = serializers.ListField(child=serializers.CharField(allow_blank=False), required=True)
    documents = PhlebotomistDocumentSerializer(many=True, required=True)

    def validate_email(self, value):
        if models.User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not any(char.isdigit() for char in value):
            raise serializers.ValidationError("Password must contain at least one digit.")
        if not any(char.isupper() for char in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(char.islower() for char in value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        if not any(char in "!@#$%^&*()_+-=[]{}|;':\",./<>?`~" for char in value):
            raise serializers.ValidationError("Password must contain at least one special character.")
        return value

    def validate_availabilities(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one availability slot is required.")
        return value

    def validate_skills(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one skill is required.")
        return value

    def validate_documents(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError("At least one document is required.")
        for doc in value:
            if not doc.get('document_file'):
                raise serializers.ValidationError("Each document must include a document file.")
        return value

    def create(self, validated_data):
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        full_name = validated_data.pop('full_name')
        phone_number = validated_data.pop('phone_number')
        gender = validated_data.pop('gender')
        dob = validated_data.pop('dob')
        role = validated_data.get('role', models.User.PHLEBOTOMIST)
        profile_picture = validated_data.pop('profile_picture', None)

        license_number = validated_data.pop('license_number')
        license_expiry_date = validated_data.pop('license_expiry_date')
        years_of_experience = validated_data.pop('years_of_experience', 0)
        specialty = validated_data.pop('specialty')
        work_preference = validated_data.pop('work_preference')
        service_area = validated_data.pop('service_area')
        address = validated_data.pop('address', None)

        availabilities_data = validated_data.pop('availabilities', [])
        skills_data = validated_data.pop('skills', [])
        documents_data = validated_data.pop('documents', [])

        from django.db import transaction
        with transaction.atomic():
            user = models.User.objects.create_user(
                email=email,
                password=password,
                full_name=full_name,
                phone_number=phone_number,
                gender=gender,
                dob=dob,
                role=role,
                profile_picture=profile_picture
            )

            phlebotomist = models.Phlebotomist.objects.create(
                user=user,
                license_number=license_number,
                license_expiry_date=license_expiry_date,
                years_of_experience=years_of_experience,
                specialty=specialty,
                work_preference=work_preference,
                service_area=service_area,
                address=address
            )

            for availability_data in availabilities_data:
                models.PhlebotomistAvailability.objects.create(
                    phlebotomist=phlebotomist,
                    **availability_data
                )

            for skill_name in skills_data:
                models.Phlebotomist_skill.objects.create(
                    phlebotomist=phlebotomist,
                    skill_name=skill_name
                )

            for doc_data in documents_data:
                models.Phlebotomist_document.objects.create(
                    phlebotomist=phlebotomist,
                    **doc_data
                )

        return user
