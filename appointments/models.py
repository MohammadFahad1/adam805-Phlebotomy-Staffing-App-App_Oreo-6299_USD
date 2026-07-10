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
    CLIENT_ASSIGNED = 'client_assigned'
    ASSIGNED = 'assigned'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    RESCHEDULED = 'rescheduled'
    NO_SHOW = 'no_show'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (CONFIRMED, 'Confirmed'),
        (ASSIGNED, 'Assigned to Phlebotomist'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (RESCHEDULED, 'Rescheduled'),
        (NO_SHOW, 'No Show'),
    ]
    patient = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='appointments')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments', null=True, blank=True)
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
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='payments', null=True, blank=True)
    job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    stripe_payment_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.appointment:
            return f"Payment for {self.appointment.patient.first_name} {self.appointment.patient.last_name} - {self.payment_status}"
        elif self.job:
            return f"Payment for Job {self.job.id} - {self.payment_status}"
        return f"Payment {self.id} - {self.payment_status}"

    class Meta:
        ordering = ['-created_at']


class PlatformSetting(models.Model):
    key = models.CharField(max_length=100, unique=True, default='platform_fee_percentage')
    value = models.DecimalField(max_digits=5, decimal_places=2, default=15.00, help_text="Fee percentage or amount value")
    description = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.value}"


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Current available withdrawable balance")
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Total gross amount earned/paid in")
    total_platform_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Total platform fee charged")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet for {self.user.email} - Balance: ${self.balance}"


class WalletTransaction(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'
    TYPE_CHOICES = [
        (CREDIT, 'Credit (Earnings/Refund/Deposit)'),
        (DEBIT, 'Debit (Payment/Withdrawal/Fee)'),
    ]
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.CharField(max_length=255)
    reference_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    reference_job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type.upper()} of ${self.amount} for {self.wallet.user.email}"


class PayoutRequest(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    COMPLETED = 'completed'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
        (COMPLETED, 'Completed'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payout_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payout Request by {self.user.email} for ${self.amount} ({self.status})"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.get_or_create(user=instance)



