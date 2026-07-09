from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class ServicePackage(models.Model):
    icon = models.ImageField(upload_to='service_package_icons/', null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"

    class Meta:
        ordering = ['price']

class ServicePackageFeature(models.Model):
    service_package = models.ForeignKey(ServicePackage, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class PatientProfile(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=False)
    phone_number = models.CharField(max_length=20)
    dob = models.DateField()
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.email}"


class Appointment(models.Model):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    ASSIGNED = 'assigned'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (ASSIGNED, 'Assigned to Phlebotomist'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (NO_SHOW, 'No Show'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    service_package = models.ForeignKey(ServicePackage, on_delete=models.PROTECT, related_name='appointments')
    appointment_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    location_type = models.CharField(max_length=50, choices=[('home', 'Patient Home'), ('hospital', 'Hospital/Clinic'), ('lab', 'Lab')])
    location = models.CharField(max_length=255)
    current_medications = models.TextField(blank=True, null=True)
    prescription = models.FileField(upload_to='prescriptions/', null=True, blank=True)
    known_allergies = models.TextField(blank=True, null=True)
    medical_conditions = models.CharField(max_length=50,choices=[('Diabetes', 'Diabetes'), ('High Blood Pressure', 'High Blood Pressure'), ('Low Blood Pressure', 'Low Blood Pressure'), ('Thyroid', 'Thyroid'), ('Heart Disease', 'Heart Disease'), ('No Medical Conditions', 'No Medical Conditions')], blank=True, null=True)
    special_requests = models.TextField(blank=True, null=True)
    email_result_notification = models.BooleanField(default=True)
    sms_appointment_reminders = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.first_name} {self.patient.last_name} - {self.service_package.name} on {self.appointment_date}"

class Payment(models.Model):
    PENDING = 'pending'
    PAID = 'paid'
    FAILED = 'failed'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAID, 'Paid'),
        (FAILED, 'Failed'),
    ]
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    stripe_payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.appointment.patient.first_name} {self.appointment.patient.last_name} - {self.payment_status}"

    class Meta:
        ordering = ['-created_at']

