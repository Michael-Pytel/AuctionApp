# email_utils.py
from django.core.mail import send_mail
from django.conf import settings
import secrets
from django.utils import timezone


def send_confirmation_email(user):
    token = secrets.token_urlsafe(48)
    user.confirmation_token = token
    user.token_created_at = timezone.now()
    user.save()

    confirmation_link = f"http://{settings.SITE_URL}/confirm-email/{token}"

    send_mail(
        'Confirm your Auctions account',
        f'''Hi {user.username},

Thank you for registering! Please confirm your email by clicking this link:
{confirmation_link}

This link will expire in 24 hours.

If you did not register for an account, please ignore this email.''',
        'noreply@auctionsite.com',
        [user.email],
        fail_silently=False,
    )