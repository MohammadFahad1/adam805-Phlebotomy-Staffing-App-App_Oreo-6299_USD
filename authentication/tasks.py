from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth import get_user_model
from django.utils import timezone
User = get_user_model()

@shared_task
def send_activation_otp_email(email, otp):
    subject = "OTP - Activate Your PrimePath Account"
    from_email = settings.EMAIL_HOST_USER 
    
    context = {"otp": otp, "purpose": "Activation"}
    html_content = render_to_string("otp_template.html", context)
    text_content = strip_tags(html_content)
    try:
        msg = EmailMultiAlternatives(
            subject, 
            text_content, 
            from_email, 
            [email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        msg.send()
        return f'Email sent to {email}'
    except Exception as e:
        return f'Error: {e}'

@shared_task
def send_reset_otp_email(email, otp):
    subject = "OTP - Reset Your PrimePath Password"
    from_email = settings.EMAIL_HOST_USER 
    
    context = {"otp": otp, "purpose": "Password Reset"}
    html_content = render_to_string("otp_template.html", context)
    text_content = strip_tags(html_content)
    try:
        msg = EmailMultiAlternatives(
            subject, 
            text_content, 
            from_email, 
            [email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        msg.send()
        return f'Email sent to {email}'
    except Exception as e:
        return f'Error: {e}'

