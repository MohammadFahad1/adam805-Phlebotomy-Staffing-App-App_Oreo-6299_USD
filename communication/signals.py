import logging
from django.db import models
from django.db.models.signals import post_save, pre_save, post_delete

logger = logging.getLogger(__name__)

def send_notification(user, title, message, notification_type, channel='in_app', reference_id=None):
    """
    Helper function to:
    1. Save notification to the Notification model (for in-app display).
    2. Send push notification via FCM if user has registered active device(s).
    3. Send email if email channel is requested.
    """
    from communication.models import Notification
    
    cleaned_ref_id = None
    if reference_id:
        import uuid
        try:
            cleaned_ref_id = uuid.UUID(str(reference_id))
        except ValueError:
            cleaned_ref_id = uuid.uuid5(uuid.NAMESPACE_DNS, str(reference_id))
    
    # 1. Save to local DB (In-App)
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        type=notification_type,
        reference_id=cleaned_ref_id
    )
    
    # 2. Push Notification via FCM
    if user.role != 'admin' and ('push' in channel.lower() or 'in-app' in channel.lower()):
        try:
            from fcm_django.models import FCMDevice
            from firebase_admin.messaging import Message, Notification as FCMNotification
            
            devices = FCMDevice.objects.filter(user=user, active=True)
            if devices.exists():
                devices.send_message(
                    Message(
                        notification=FCMNotification(
                            title=title,
                            body=message
                        )
                    )
                )
        except Exception as e:
            logger.error(f"Error sending push notification to user {user.id}: {e}")
            
    # 3. Email Notification
    if 'email' in channel.lower():
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject=title,
                message=message,
                from_email=settings.EMAIL_HOST_USER or 'noreply@phlebotomystaffing.com',
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Error sending email to user {user.id}: {e}")


def send_admin_notification(title, message, notification_type, channel='in_app', reference_id=None):
    """
    Helper function to send database notifications to all admin users.
    Admins only receive database notifications and emails if requested.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Get all admin/staff/superuser accounts
    admins = User.objects.filter(models.Q(role='admin') | models.Q(is_staff=True) | models.Q(is_superuser=True))
    for admin in admins:
        send_notification(admin, title, message, notification_type, channel=channel, reference_id=reference_id)


# ── 1. Profile Approval Signals ───────────────────────────────────────────────

def phlebotomist_profile_approved(sender, instance, created, **kwargs):
    from authentication.models import Phlebotomist
    if not isinstance(instance, Phlebotomist):
        return
        
    if instance.approved is True:
        from communication.models import Notification
        title = "Account Approved"
        message = "Your Phlebotomist profile has been approved by the administrator. You can now log in."
        
        # Prevent duplicate notifications if already notified
        if not Notification.objects.filter(user=instance.user, title=title, type='account_status').exists():
            send_notification(instance.user, title, message, 'account_status', channel='Email')


def client_profile_approved(sender, instance, created, **kwargs):
    from authentication.models import Client
    if not isinstance(instance, Client):
        return
        
    if instance.is_approved is True:
        from communication.models import Notification
        title = "Account Approved"
        message = "Your Client profile has been approved by the administrator. You can now log in."
        
        # Prevent duplicate notifications if already notified
        if not Notification.objects.filter(user=instance.client, title=title, type='account_status').exists():
            send_notification(instance.client, title, message, 'account_status', channel='Email')


# ── 2. Job Assignment & Status Signals ────────────────────────────────────────

def job_assignment_pre_save(sender, instance, **kwargs):
    from jobs.models import JobAssignment
    if not isinstance(instance, JobAssignment):
        return
        
    if instance.id:
        try:
            instance._old_status = JobAssignment.objects.get(id=instance.id).status
        except JobAssignment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


def job_assignment_post_save(sender, instance, created, **kwargs):
    from jobs.models import JobAssignment
    if not isinstance(instance, JobAssignment):
        return
        
    old_status = getattr(instance, '_old_status', None)
    
    # 2.1 New Job Assigned by Client (for Phlebotomist)
    if created:
        title = "Job Assigned"
        message = f"You have been assigned to the job: '{instance.job.title}'."
        send_notification(instance.phlebotomist, title, message, 'job_alert', channel='In-App / Push', reference_id=instance.job.id)
        
    # 2.2 Job Assignment Accepted (for Client)
    elif old_status != JobAssignment.ACTIVE and instance.status == JobAssignment.ACTIVE:
        phlebotomist_name = instance.phlebotomist.full_name
        title = "Job Accepted"
        message = f"{phlebotomist_name} has accepted your job assignment: '{instance.job.title}'."
        send_notification(instance.client, title, message, 'job_alert', channel='In-App / Push', reference_id=instance.job.id)
        
    # 2.3 Job Marked as Completed (for Client)
    elif old_status != JobAssignment.COMPLETED and instance.status == JobAssignment.COMPLETED:
        phlebotomist_name = instance.phlebotomist.full_name
        title = "Job Completed"
        message = f"{phlebotomist_name} has marked the job '{instance.job.title}' as completed. Please review and pay."
        send_notification(instance.client, title, message, 'job_alert', channel='In-App / Push', reference_id=instance.job.id)


def job_assignment_deleted(sender, instance, **kwargs):
    from jobs.models import JobAssignment
    if not isinstance(instance, JobAssignment):
        return
        
    # If the assignment was pending or active when deleted, it means it was rejected/declined
    if instance.status in [JobAssignment.PENDING, JobAssignment.ACTIVE]:
        phlebotomist_name = instance.phlebotomist.full_name
        title = "Job Declined"
        message = f"{phlebotomist_name} has declined your job assignment: '{instance.job.title}'."
        send_notification(instance.client, title, message, 'job_alert', channel='In-App / Push', reference_id=instance.job.id)


# ── 3. Job Application Signals ────────────────────────────────────────────────

def job_application_pre_save(sender, instance, **kwargs):
    from jobs.models import JobApplication
    if not isinstance(instance, JobApplication):
        return
        
    if instance.id:
        try:
            instance._old_status = JobApplication.objects.get(id=instance.id).status
        except JobApplication.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


def job_application_post_save(sender, instance, created, **kwargs):
    from jobs.models import JobApplication
    if not isinstance(instance, JobApplication):
        return
        
    old_status = getattr(instance, '_old_status', None)
    
    # 3.1 New Job Application (for Client)
    if created:
        phlebotomist_name = instance.phlebotomist.full_name
        title = "New Application"
        message = f"{phlebotomist_name} has applied to your job posting: '{instance.job.title}'."
        send_notification(instance.job.client, title, message, 'application_update', channel='In-App / Push', reference_id=instance.job.id)
        
    # 3.2 Job Application Status Change (for Phlebotomist)
    elif old_status != instance.status:
        if instance.status == JobApplication.ACCEPTED:
            title = "Application Update"
            message = f"Your application for the job '{instance.job.title}' has been accepted."
            send_notification(instance.phlebotomist, title, message, 'application_update', channel='In-App / Push', reference_id=instance.job.id)
        elif instance.status == JobApplication.REJECTED:
            title = "Application Update"
            message = f"Your application for the job '{instance.job.title}' has been declined."
            send_notification(instance.phlebotomist, title, message, 'application_update', channel='In-App / Push', reference_id=instance.job.id)


# ── 4. Payment Signals ────────────────────────────────────────────────────────

def payment_pre_save(sender, instance, **kwargs):
    from appointments.models import Payment
    if not isinstance(instance, Payment):
        return
        
    if instance.id:
        try:
            instance._old_status = Payment.objects.get(id=instance.id).payment_status
        except Payment.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


def payment_post_save(sender, instance, created, **kwargs):
    from appointments.models import Payment
    if not isinstance(instance, Payment):
        return
        
    old_status = getattr(instance, '_old_status', None)
    
    # Payment Received for Job (for Phlebotomist)
    if old_status != Payment.PAID and instance.payment_status == Payment.PAID:
        if instance.job:
            # Locate the phlebotomist who worked on the job
            assignment = getattr(instance.job, 'assignment', None)
            if assignment:
                title = "Payment Received"
                message = f"Your payment of ${instance.amount:.2f} for '{instance.job.title}' has been processed to your wallet."
                send_notification(assignment.phlebotomist, title, message, 'payment', channel='In-App / Push / Email', reference_id=instance.job.id)


# ── 5. Payout Request Signals ─────────────────────────────────────────────────

def payout_request_pre_save(sender, instance, **kwargs):
    from appointments.models import PayoutRequest
    if not isinstance(instance, PayoutRequest):
        return
        
    if instance.id:
        try:
            instance._old_status = PayoutRequest.objects.get(id=instance.id).status
        except PayoutRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


def payout_request_post_save(sender, instance, created, **kwargs):
    from appointments.models import PayoutRequest
    if not isinstance(instance, PayoutRequest):
        return
        
    old_status = getattr(instance, '_old_status', None)
    
    # 5.1 New Payout Request Submitted (for Admin)
    if created:
        title = "Payout Requested"
        message = f"Phlebotomist {instance.user.full_name} has requested a payout of ${instance.amount:.2f}."
        send_admin_notification(title, message, 'financial_alert', channel='In-App / Email')
        
    # 5.2 Payout Request Status Change (for Phlebotomist)
    elif old_status != instance.status:
        if instance.status in [PayoutRequest.APPROVED, PayoutRequest.COMPLETED]:
            title = "Payout Status Update"
            message = f"Your payout request of ${instance.amount:.2f} has been approved and processed."
            send_notification(instance.user, title, message, 'payout_status', channel='In-App / Push / Email')
        elif instance.status == PayoutRequest.REJECTED:
            title = "Payout Status Update"
            message = f"Your payout request of ${instance.amount:.2f} has been rejected."
            send_notification(instance.user, title, message, 'payout_status', channel='In-App / Push / Email')


# ── 6. Message Signals ────────────────────────────────────────────────────────

def message_created(sender, instance, created, **kwargs):
    from communication.models import Message
    if not isinstance(instance, Message):
        return
        
    if created:
        sender_name = instance.sender.full_name
        truncated_text = instance.message_text[:50] + '...' if len(instance.message_text) > 50 else instance.message_text
        
        # Display "Client {Name}" if sender is client, otherwise just the name
        if instance.sender.role == 'client':
            sender_label = f"Client {sender_name}"
        else:
            sender_label = sender_name
            
        title = "New Message"
        message = f"{sender_label} sent you a message: '{truncated_text}'"
        
        send_notification(instance.receiver, title, message, 'message', channel='In-App / Push')


# ── 7. Patient Appointment Booked Signals ─────────────────────────────────────

def appointment_created(sender, instance, created, **kwargs):
    from appointments.models import Appointment
    if not isinstance(instance, Appointment):
        return
        
    if created and instance.client:
        patient_name = f"{instance.patient.first_name} {instance.patient.last_name}"
        title = "Appointment Booked"
        message = f"New patient appointment for {patient_name} has been successfully booked."
        send_notification(instance.client, title, message, 'appointment_update', channel='In-App / Push')


# ── 8. OTP Code Verification Signals ──────────────────────────────────────────

def user_pre_save(sender, instance, **kwargs):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not isinstance(instance, User):
        return
        
    if instance.id:
        try:
            instance._old_otp = User.objects.get(id=instance.id).otp
        except User.DoesNotExist:
            instance._old_otp = None
    else:
        instance._old_otp = None


def user_post_save(sender, instance, created, **kwargs):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not isinstance(instance, User):
        return
        
    old_otp = getattr(instance, '_old_otp', None)
    if instance.otp and instance.otp != old_otp:
        title = "Verification OTP"
        if instance.role == 'admin' or instance.is_staff or instance.is_superuser:
            message = f"Your admin login OTP code is {instance.otp}. It is valid for 10 minutes."
        else:
            message = f"Your verification OTP code is {instance.otp}. It is valid for 10 minutes."
            
        send_notification(instance, title, message, 'security', channel='Email')


# ── 9. Admin Notification Signals ─────────────────────────────────────────────

def phlebotomist_registered_alert(sender, instance, created, **kwargs):
    from authentication.models import Phlebotomist
    if not isinstance(instance, Phlebotomist):
        return
    if created:
        title = "Registration Alert"
        message = f"New Phlebotomist registration: {instance.user.full_name} is pending approval."
        send_admin_notification(title, message, 'system_alert', channel='In-App / Email')


def client_registered_alert(sender, instance, created, **kwargs):
    from authentication.models import Client
    if not isinstance(instance, Client):
        return
    if created:
        title = "Registration Alert"
        message = f"New Client registration: {instance.client.full_name} is pending approval."
        send_admin_notification(title, message, 'system_alert', channel='In-App / Email')


def report_created_alert(sender, instance, created, **kwargs):
    from communication.models import Report
    if not isinstance(instance, Report):
        return
        
    if created:
        reporter_role = "Phlebotomist" if instance.reporter.role == 'phlebotomist' else "Client"
        reported_role = "Phlebotomist" if instance.reported_user.role == 'phlebotomist' else "Client"
        
        title = "Moderation Alert"
        message = f"{reported_role} {instance.reported_user.full_name} has been reported by {reporter_role} {instance.reporter.full_name}."
        send_admin_notification(title, message, 'moderation_alert', channel='In-App / Email')


# ── 10. Dynamic Receiver Registration ─────────────────────────────────────────

def register_signals():
    """
    Connect receivers to models dynamically to avoid import-time side effects
    and Django's AppRegistryNotReady exceptions.
    """
    from authentication.models import User, Phlebotomist, Client
    from jobs.models import JobAssignment, JobApplication
    from appointments.models import Payment, PayoutRequest, Appointment
    from communication.models import Message, Report
    
    # Profile Approval & Registration Alerts
    post_save.connect(phlebotomist_profile_approved, sender=Phlebotomist, dispatch_uid='phlebotomist_profile_approved_sig')
    post_save.connect(phlebotomist_registered_alert, sender=Phlebotomist, dispatch_uid='phlebotomist_registered_alert_sig')
    post_save.connect(client_profile_approved, sender=Client, dispatch_uid='client_profile_approved_sig')
    post_save.connect(client_registered_alert, sender=Client, dispatch_uid='client_registered_alert_sig')
    
    # Job Assignment
    pre_save.connect(job_assignment_pre_save, sender=JobAssignment, dispatch_uid='job_assignment_pre_save_sig')
    post_save.connect(job_assignment_post_save, sender=JobAssignment, dispatch_uid='job_assignment_post_save_sig')
    post_delete.connect(job_assignment_deleted, sender=JobAssignment, dispatch_uid='job_assignment_deleted_sig')
    
    # Job Application
    pre_save.connect(job_application_pre_save, sender=JobApplication, dispatch_uid='job_application_pre_save_sig')
    post_save.connect(job_application_post_save, sender=JobApplication, dispatch_uid='job_application_post_save_sig')
    
    # Payments & Payouts
    pre_save.connect(payment_pre_save, sender=Payment, dispatch_uid='payment_pre_save_sig')
    post_save.connect(payment_post_save, sender=Payment, dispatch_uid='payment_post_save_sig')
    pre_save.connect(payout_request_pre_save, sender=PayoutRequest, dispatch_uid='payout_request_pre_save_sig')
    post_save.connect(payout_request_post_save, sender=PayoutRequest, dispatch_uid='payout_request_post_save_sig')
    
    # Messages & Appointments & OTP
    post_save.connect(message_created, sender=Message, dispatch_uid='message_created_sig')
    post_save.connect(appointment_created, sender=Appointment, dispatch_uid='appointment_created_sig')
    pre_save.connect(user_pre_save, sender=User, dispatch_uid='user_pre_save_sig')
    post_save.connect(user_post_save, sender=User, dispatch_uid='user_post_save_sig')
    
    # Reports
    post_save.connect(report_created_alert, sender=Report, dispatch_uid='report_created_alert_sig')
