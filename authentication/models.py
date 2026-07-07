from django.db import models
from django.contrib.auth.models import AbstractUser
from authentication.managers import CustomUserManager

class User(AbstractUser):
    PHLEBOTOMIST = 'phlebotomist'
    CLIENT = 'client'
    ADMIN = 'admin'
    ROLE_CHOICES = [
        (PHLEBOTOMIST, 'Phlebotomist'),
        (CLIENT, 'Client'),
        (ADMIN, 'Admin'),
    ]
    
    MALE = 'male'
    FEMALE = 'female'
    GENDER_CHOICES = [
        (MALE, 'Male'),
        (FEMALE, 'Female'),
    ]
    username = None
    first_name = None
    last_name = None
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    gender = models.CharField(choices=GENDER_CHOICES, max_length=10)
    dob = models.DateField()
    role = models.CharField(choices=ROLE_CHOICES, max_length=20)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    forgot_password_token = models.CharField(max_length=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone_number', 'gender', 'dob', 'role']
    
    objects = CustomUserManager()
    
    class Meta:
        ordering = ['is_superuser', 'is_staff', '-created_at']
    
    def __str__(self):
        return f"#{self.id} - {self.full_name} ({self.email})"

# Phlebotomist models Start Here
class Phlebotomist(models.Model):
    GENERAL_PHLEBOTOMY = 'general_phlebotomy'
    IV_INSERTION_OR_THERAPY = 'iv_insertion_or_therapy'
    ONCOLOGY_OR_CHEMOTHERAPY = 'oncology_or_chemotherapy'
    MEDICAL_NURSE = 'medical_nurse'
    SPECIALTY_CHOICES = [
        (GENERAL_PHLEBOTOMY, 'General Phlebotomy'),
        (IV_INSERTION_OR_THERAPY, 'IV Insertion/Therapy'),
        (ONCOLOGY_OR_CHEMOTHERAPY, 'Oncology/Chemotherapy'),
        (MEDICAL_NURSE, 'Medical Nurse'),
    ]
    
    PART_TIME = 'part_time'
    FULL_TIME = 'full_time'
    WORK_PREFERENCE_CHOICES = [
        (PART_TIME, 'Part-time'),
        (FULL_TIME, 'Full-time'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='phlebotomist_profile')
    license_number = models.CharField(max_length=100)
    license_expiry_date = models.DateField()
    years_of_experience = models.PositiveIntegerField(default=0)
    specialty = models.CharField(choices=SPECIALTY_CHOICES, max_length=100)
    work_preference = models.CharField(choices=WORK_PREFERENCE_CHOICES, max_length=100)
    service_area = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    approved = models.BooleanField(default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Phlebotomist: {self.user.full_name} (License: {self.license_number})"

class PhlebotomistAvailability(models.Model):
    phlebotomist = models.ForeignKey(Phlebotomist, on_delete=models.CASCADE, related_name='availabilities')
    day = models.CharField(max_length=10)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('phlebotomist', 'date', 'start_time', 'end_time')
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"Availability for {self.phlebotomist.user.full_name} on {self.date} from {self.start_time} to {self.end_time}"

class Phlebotomist_skill(models.Model):
    phlebotomist = models.ForeignKey(Phlebotomist, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ('phlebotomist', 'skill_name')
    
    def __str__(self):
        return f"Skill: {self.skill_name} for {self.phlebotomist.user.full_name}"

class Phlebotomist_document(models.Model):
    LICENSE = 'license'
    IDENTIFICATION = 'identification'
    DOCUMENT_TYPE_CHOICES = [
        (LICENSE, 'License'),
        (IDENTIFICATION, 'Identification'),
    ]
    phlebotomist = models.ForeignKey(Phlebotomist, on_delete=models.CASCADE, related_name='documents')
    document_name = models.CharField(max_length=100, choices=DOCUMENT_TYPE_CHOICES)
    document_file = models.FileField(upload_to='phlebotomist_documents/')
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('phlebotomist', 'document_name', 'approved')
    
    def __str__(self):
        return f"Document: {self.document_name} for {self.phlebotomist.user.full_name}"
# Phlebotomist models End Here

# Client models Start Here
class Client(models.Model):
    HEALTHCARE = 'healthcare'
    INDIVIDUAL = 'individual'
    BUSINESS_TYPE_CHOICES = [
        (HEALTHCARE, 'Healthcare'),
        (INDIVIDUAL, 'Individual'),
    ]
    
    IN_CLINIC_PHLEBOTOMY = 'in_clinic_phlebotomy'
    MOBILE_BLOOD_DRAW = 'mobile_blood_draw'
    LABORATORY_TESTING = 'laboratory_testing'
    JOB_PREFERENCE_CHOICES = [
        (IN_CLINIC_PHLEBOTOMY, 'In-Clinic Phlebotomy'),
        (MOBILE_BLOOD_DRAW, 'Mobile Blood Draw'),
        (LABORATORY_TESTING, 'Laboratory Testing'),
    ]
    
    PART_TIME = 'part_time'
    FULL_TIME = 'full_time'
    WORK_PREFERENCE_CHOICES = [
        (PART_TIME, 'Part-time'),
        (FULL_TIME, 'Full-time'),
    ]
    client = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
    business_name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=255, choices=BUSINESS_TYPE_CHOICES)
    business_address_street = models.CharField(max_length=255)
    business_address_city = models.CharField(max_length=255)
    business_address_state = models.CharField(max_length=255)
    business_address_zip = models.CharField(max_length=10)
    contact_person_name = models.CharField(max_length=255)
    business_phone = models.CharField(max_length=20)
    business_license_number = models.CharField(max_length=100)
    business_description = models.TextField()
    hourly_pay_rate = models.DecimalField(max_digits=10, decimal_places=2)
    preferred_job_type = models.CharField(max_length=100, choices=JOB_PREFERENCE_CHOICES)
    work_preference = models.CharField(max_length=100, choices=WORK_PREFERENCE_CHOICES)
    no_of_employees = models.PositiveIntegerField(default=0)
    signature = models.ImageField(upload_to='client_signatures/', null=True, blank=True)
    is_approved = models.BooleanField(default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Client: {self.client.full_name}"

class ClientDocument(models.Model):
    LICENSE = 'license'
    SIGNATURE = 'signature'
    DOCUMENT_TYPE_CHOICES = [
        (LICENSE, 'License'),
        (SIGNATURE, 'signature'),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    document_name = models.CharField(max_length=100, choices=DOCUMENT_TYPE_CHOICES)
    document_file = models.FileField(upload_to='client_documents/')
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('client', 'document_name', 'approved')
    
    def __str__(self):
        return f"Document: {self.document_name} for {self.client.client.full_name}"

class ClientWeeklySchedule(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='availabilities')
    day = models.CharField(max_length=10)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('client', 'date', 'start_time', 'end_time')
        ordering = ['date', 'start_time']
    
    def __str__(self):
        return f"Availability for {self.client.client.full_name} on {self.date} from {self.start_time} to {self.end_time}"
# Client models End Here