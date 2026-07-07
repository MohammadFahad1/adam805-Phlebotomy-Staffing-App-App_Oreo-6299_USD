from django.db import models
from django.conf import settings

class Job(models.Model):
    DRAFT = 'draft'
    PENDING_APPROVAL = 'pending_approval'
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING_APPROVAL, 'Pending Approval'),
        (OPEN, 'Open'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    REGISTERED_NURSE = 'RN'
    LICENSED_PRACTICAL_NURSE = 'LPN'
    CERTIFIED_PHLEBOTOMIST = 'CP'
    PROFESSIONAL_TYPE_CHOICES = [
        (REGISTERED_NURSE, 'Registered Nurse (RN)'),
        (LICENSED_PRACTICAL_NURSE, 'Licensed Practical Nurse'),
        (CERTIFIED_PHLEBOTOMIST, 'Certified Phlebotomist'),
    ]
    
    HOURLY = 'hourly'
    FLAT_RATE = 'flat_rate'
    PAY_TYPE_CHOICES = [
        (HOURLY, 'Hourly'),
        (FLAT_RATE, 'Flat Rate'),
    ]
    
    URGENT = 'urgent'
    FULL_DAY = 'full_day'
    PART_TIME = 'part_time'
    JOB_TYPE_CHOICES = [
        (URGENT, 'Urgent'),
        (FULL_DAY, 'Full Day'),
        (PART_TIME, 'Part Time'),
    ]
    job_id = models.CharField(max_length=20, unique=True, blank=True, editable=False, db_index=True)
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='jobs') 
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.TextField()
    city = models.CharField(max_length=100, null=True, blank=True)
    shift_duration = models.IntegerField(default=0)  # Duration in hours
    shift_date = models.DateField() 
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    duration_hours = models.IntegerField(blank=True, null=True)
    pay_type = models.CharField(max_length=50, choices=PAY_TYPE_CHOICES, default=HOURLY)
    pay_rate = models.DecimalField(max_digits=10, decimal_places=2)
    professional_type = models.CharField(max_length=100, choices=PROFESSIONAL_TYPE_CHOICES, default=CERTIFIED_PHLEBOTOMIST)
    job_type = models.CharField(max_length=100, choices=JOB_TYPE_CHOICES, default=FULL_DAY)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default=PENDING_APPROVAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # After first insert pk is a real integer — generate job_id
        if not self.job_id:
            year = self.created_at.year
            self.job_id = f"JB-{str(year)[-2:]}-{self.pk:06d}"
            Job.objects.filter(pk=self.pk).update(job_id=self.job_id)

    def __str__(self):
        return f"{self.job_id} - {self.title}"

class JobApplication(models.Model):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    WITHDRAWN = 'withdrawn'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REJECTED, 'Rejected'),
        (WITHDRAWN, 'Withdrawn'),
    ]
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='applications')
    phlebotomist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='job_applications')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('job', 'phlebotomist')

    def __str__(self):
        return f"{self.job} - {self.phlebotomist}"

class JobAssignment(models.Model):
    PENDING = 'pending'
    ACTIVE = 'active'
    COMPLETED = 'completed'
    DISPUTED = 'disputed'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACTIVE, 'Active'),
        (COMPLETED, 'Completed'),
        (DISPUTED, 'Disputed'),
    ]
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='assignment')
    phlebotomist = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignments')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_assignments')
    contract_url = models.TextField(null=True, blank=True)
    signed_by_phlebotomist = models.BooleanField(default=False)
    signed_by_client = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=PENDING)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job} - {self.phlebotomist} - {self.status}"

class JobTemplate(models.Model):
    DRAFT = 'draft'
    PENDING_APPROVAL = 'pending_approval'
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING_APPROVAL, 'Pending Approval'),
        (OPEN, 'Open'),
        (IN_PROGRESS, 'In Progress'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    REGISTERED_NURSE = 'RN'
    LICENSED_PRACTICAL_NURSE = 'LPN'
    CERTIFIED_PHLEBOTOMIST = 'CP'
    PROFESSIONAL_TYPE_CHOICES = [
        (REGISTERED_NURSE, 'Registered Nurse (RN)'),
        (LICENSED_PRACTICAL_NURSE, 'Licensed Practical Nurse'),
        (CERTIFIED_PHLEBOTOMIST, 'Certified Phlebotomist'),
    ]
    
    HOURLY = 'hourly'
    FLAT_RATE = 'flat_rate'
    PAY_TYPE_CHOICES = [
        (HOURLY, 'Hourly'),
        (FLAT_RATE, 'Flat Rate'),
    ]
    
    URGENT = 'urgent'
    FULL_DAY = 'full_day'
    PART_TIME = 'part_time'
    JOB_TYPE_CHOICES = [
        (URGENT, 'Urgent'),
        (FULL_DAY, 'Full Day'),
        (PART_TIME, 'Part Time'),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.TextField()
    city = models.CharField(max_length=100, null=True, blank=True)
    shift_duration = models.IntegerField(default=0)  # Duration in hours
    shift_date = models.DateField() 
    shift_start = models.TimeField()
    shift_end = models.TimeField()
    duration_hours = models.IntegerField()
    pay_type = models.CharField(max_length=50, choices=PAY_TYPE_CHOICES, default=HOURLY)
    pay_rate = models.DecimalField(max_digits=10, decimal_places=2)
    professional_type = models.CharField(max_length=100, choices=PROFESSIONAL_TYPE_CHOICES, default=CERTIFIED_PHLEBOTOMIST)
    job_type = models.CharField(max_length=100, choices=JOB_TYPE_CHOICES, default=FULL_DAY)
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default=PENDING_APPROVAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.title}"


