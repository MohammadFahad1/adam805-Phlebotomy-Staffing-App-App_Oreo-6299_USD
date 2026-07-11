from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Message(models.Model):
    sender = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='received_messages')
    job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True)
    message_text = models.TextField()
    is_read = models.BooleanField(default=False)
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver} - Read: {self.is_read}"

class Review(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='reviews_as_reviewer')
    reviewed = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='reviews_as_reviewed')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review from {self.reviewer} to {self.reviewed} - Rating: {self.rating} - Comment: {self.comment}"

class Notification(models.Model):
    user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=50)  # job_alert, application_update, payment, etc.
    is_read = models.BooleanField(default=False)
    reference_id = models.UUIDField(null=True, blank=True)  # job_id, application_id, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user}: {self.message}"

class Report(models.Model):
    INAPPROPRIATE_LANGUAGE = 'inappropriate_language'
    HARASSMENT = 'harassment'
    SPAM = 'spam'
    FAKE_PROFILE = 'fake_profile'
    OTHER = 'other'
    REASON_CHOICES = [
        (INAPPROPRIATE_LANGUAGE, 'Inappropriate Language'),
        (HARASSMENT, 'Harassment'),
        (SPAM, 'Spam'),
        (FAKE_PROFILE, 'Fake Profile'),
        (OTHER, 'Other'),
    ]
    
    PENDING = 'pending'
    REVIEWED = 'reviewed'
    RESOLVED = 'resolved'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (REVIEWED, 'Reviewed'),
        (RESOLVED, 'Resolved'),
    ]
    reporter = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='reports_made')
    reported_user = models.ForeignKey('authentication.User', on_delete=models.CASCADE, related_name='reports_received')
    job = models.ForeignKey('jobs.Job', on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=255, choices=REASON_CHOICES)
    additional_details = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=PENDING)
    admin_notes = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey('authentication.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_resolved')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter} against {self.reported_user} - Status: {self.status}"

