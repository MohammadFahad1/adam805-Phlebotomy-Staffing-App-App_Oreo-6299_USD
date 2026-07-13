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

# Client Serializers
class ClientWeeklyScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ClientWeeklySchedule
        fields = ['id', 'day', 'date', 'start_time', 'end_time', 'is_available']

class ClientDocumentSerializer(serializers.ModelSerializer):
    document_file = serializers.FileField(required=True, allow_null=False)

    class Meta:
        model = models.ClientDocument
        fields = ['id', 'document_name', 'document_file', 'approved']
        read_only_fields = ['approved']

class ClientSerializer(serializers.ModelSerializer):
    availabilities = ClientWeeklyScheduleSerializer(many=True, read_only=True)
    documents = ClientDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = models.Client
        fields = [
            'id',
            'business_name',
            'business_type',
            'business_address_street',
            'business_address_city',
            'business_address_state',
            'business_address_zip',
            'contact_person_name',
            'business_phone',
            'business_license_number',
            'business_description',
            'hourly_pay_rate',
            'preferred_job_type',
            'work_preference',
            'no_of_employees',
            'signature',
            'availabilities',
            'documents',
            'created_at',
            'updated_at'
        ]

class UserSerializer(serializers.ModelSerializer):
    phlebotomist_profile = PhlebotomistSerializer(read_only=True)
    client_profile = ClientSerializer(read_only=True)

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
            'client_profile',
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
    # specialty = serializers.ChoiceField(choices=models.Phlebotomist.SPECIALTY_CHOICES)
    specialty = serializers.CharField()
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

class ClientRegistrationSerializer(serializers.Serializer):
    # User fields
    full_name = serializers.CharField(required=True, allow_blank=False)
    email = serializers.EmailField(required=True, allow_blank=False)
    password = serializers.CharField(write_only=True, required=True, allow_blank=False)
    phone_number = serializers.CharField(required=True, allow_blank=False)
    gender = serializers.ChoiceField(choices=models.User.GENDER_CHOICES, required=True)
    dob = serializers.DateField(required=True)
    role = serializers.ChoiceField(choices=models.User.ROLE_CHOICES, default=models.User.CLIENT, required=False)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    # Client profile fields
    business_name = serializers.CharField(required=True, allow_blank=False)
    # business_type = serializers.ChoiceField(choices=models.Client.BUSINESS_TYPE_CHOICES, required=True)
    business_type = serializers.CharField(required=True, allow_blank=False)
    business_address_street = serializers.CharField(required=True, allow_blank=False)
    business_address_city = serializers.CharField(required=True, allow_blank=False)
    business_address_state = serializers.CharField(required=True, allow_blank=False)
    business_address_zip = serializers.CharField(required=True, allow_blank=False)
    contact_person_name = serializers.CharField(required=True, allow_blank=False)
    business_phone = serializers.CharField(required=True, allow_blank=False)
    business_license_number = serializers.CharField(required=True, allow_blank=False)
    business_description = serializers.CharField(required=True, allow_blank=False, style={'base_template': 'textarea.html'})
    hourly_pay_rate = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)
    # preferred_job_type = serializers.ChoiceField(choices=models.Client.JOB_PREFERENCE_CHOICES, required=True)
    # work_preference = serializers.ChoiceField(choices=models.Client.WORK_PREFERENCE_CHOICES, required=True)
    preferred_job_type = serializers.CharField(required=True, allow_blank=False)
    work_preference = serializers.CharField(required=True, allow_blank=False)
    no_of_employees = serializers.IntegerField(min_value=0, required=False, default=0)
    signature = serializers.ImageField(required=True, allow_null=False)

    # Nested fields
    availabilities = ClientWeeklyScheduleSerializer(many=True, required=True)
    documents = ClientDocumentSerializer(many=True, required=True)

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
        role = validated_data.get('role', models.User.CLIENT)
        profile_picture = validated_data.pop('profile_picture', None)

        business_name = validated_data.pop('business_name')
        business_type = validated_data.pop('business_type')
        business_address_street = validated_data.pop('business_address_street')
        business_address_city = validated_data.pop('business_address_city')
        business_address_state = validated_data.pop('business_address_state')
        business_address_zip = validated_data.pop('business_address_zip')
        contact_person_name = validated_data.pop('contact_person_name')
        business_phone = validated_data.pop('business_phone')
        business_license_number = validated_data.pop('business_license_number')
        business_description = validated_data.pop('business_description')
        hourly_pay_rate = validated_data.pop('hourly_pay_rate')
        preferred_job_type = validated_data.pop('preferred_job_type')
        work_preference = validated_data.pop('work_preference')
        no_of_employees = validated_data.pop('no_of_employees', 0)
        signature = validated_data.pop('signature')

        availabilities_data = validated_data.pop('availabilities', [])
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

            client = models.Client.objects.create(
                client=user,
                business_name=business_name,
                business_type=business_type,
                business_address_street=business_address_street,
                business_address_city=business_address_city,
                business_address_state=business_address_state,
                business_address_zip=business_address_zip,
                contact_person_name=contact_person_name,
                business_phone=business_phone,
                business_license_number=business_license_number,
                business_description=business_description,
                hourly_pay_rate=hourly_pay_rate,
                preferred_job_type=preferred_job_type,
                work_preference=work_preference,
                no_of_employees=no_of_employees,
                signature=signature
            )

            for availability_data in availabilities_data:
                models.ClientWeeklySchedule.objects.create(
                    client=client,
                    **availability_data
                )

            for doc_data in documents_data:
                models.ClientDocument.objects.create(
                    client=client,
                    **doc_data
                )

        return user

class EmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=models.User.ROLE_CHOICES, required=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    forgot_password_token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)

class EmptySerializer(serializers.Serializer):
    pass


# Profile Update Serializers
class AvailabilitySlotSerializer(serializers.Serializer):
    class Meta:
        ref_name = 'AuthAvailabilitySlot'

    day = serializers.CharField()
    date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    is_available = serializers.BooleanField(default=True, required=False)


class PhlebotomistProfileUpdateSerializer(serializers.Serializer):
    """All fields optional — send only what you want to change."""
    # User fields
    full_name = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    gender = serializers.ChoiceField(choices=models.User.GENDER_CHOICES, required=False)
    dob = serializers.DateField(required=False)
    
    # Profile fields
    license_number = serializers.CharField(required=False)
    license_expiry_date = serializers.DateField(required=False)
    years_of_experience = serializers.IntegerField(required=False, min_value=0)
    # specialty = serializers.ChoiceField(choices=models.Phlebotomist.SPECIALTY_CHOICES, required=False)
    specialty = serializers.CharField()
    work_preference = serializers.ChoiceField(choices=models.Phlebotomist.WORK_PREFERENCE_CHOICES, required=False)
    service_area = serializers.CharField(required=False)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    # Nested — full replace
    skills = serializers.ListField(child=serializers.CharField(), required=False)
    availabilities = AvailabilitySlotSerializer(many=True, required=False)


class ClientProfileUpdateSerializer(serializers.Serializer):
    """All fields optional — send only what you want to change."""
    # User fields
    full_name = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)
    gender = serializers.ChoiceField(choices=models.User.GENDER_CHOICES, required=False)
    dob = serializers.DateField(required=False)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    # Profile fields
    business_name = serializers.CharField(required=False)
    # business_type = serializers.ChoiceField(choices=models.Client.BUSINESS_TYPE_CHOICES, required=False)
    business_type = serializers.CharField(required=False, allow_blank=False)
    business_address_street = serializers.CharField(required=False)
    business_address_city = serializers.CharField(required=False)
    business_address_state = serializers.CharField(required=False)
    business_address_zip = serializers.CharField(required=False)
    contact_person_name = serializers.CharField(required=False)
    business_phone = serializers.CharField(required=False)
    business_license_number = serializers.CharField(required=False)
    business_description = serializers.CharField(required=False, style={'base_template': 'textarea.html'})
    hourly_pay_rate = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    # preferred_job_type = serializers.ChoiceField(choices=models.Client.JOB_PREFERENCE_CHOICES, required=False)
    # work_preference = serializers.ChoiceField(choices=models.Client.WORK_PREFERENCE_CHOICES, required=False)
    preferred_job_type = serializers.CharField(required=True, allow_blank=False)
    work_preference = serializers.CharField(required=True, allow_blank=False)
    no_of_employees = serializers.IntegerField(required=False, min_value=0)
    
    # Nested — full replace
    availabilities = AvailabilitySlotSerializer(many=True, required=False)
