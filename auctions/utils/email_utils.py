# email_utils.py

import secrets

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.conf import settings
from django.contrib import messages
from auctions.models import User


def send_confirmation_email(user, request=None):
    """
    Send email confirmation to user

    Args:
        user: User object
        request: HttpRequest object (optional, for getting domain)
    """
    # Generate token
    token = secrets.token_urlsafe(48)
    user.confirmation_token = token
    user.token_created_at = timezone.now()
    user.save()

    # Get site domain dynamically (handles both dev and production)
    if request:
        current_site = get_current_site(request)
        domain = current_site.domain
        protocol = 'https' if request.is_secure() else 'http'
    else:
        # Fallback if no request object
        domain = getattr(settings, 'SITE_URL', 'localhost:8000')
        protocol = 'https' if not settings.DEBUG else 'http'

    confirmation_link = f"{protocol}://{domain}/confirm-email/{token}"

    # Plain text message
    plain_message = f'''Hi {user.username},

Thank you for registering! Please confirm your email by clicking this link:
{confirmation_link}

This link will expire in 24 hours.

If you did not register for an account, please ignore this email.

Best regards,
The AuctionApp Team'''

    # HTML message (optional but recommended for better appearance)
    html_message = f'''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Welcome to AuctionApp!</h2>

        <p>Hi {user.username},</p>

        <p>Thank you for registering! Please confirm your email address to activate your account.</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{confirmation_link}" 
               style="background-color: #4CAF50; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block; 
                      font-weight: bold;">
                Confirm Email Address
            </a>
        </div>

        <p style="color: #666; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <a href="{confirmation_link}" style="color: #4CAF50; word-break: break-all;">
                {confirmation_link}
            </a>
        </p>

        <p style="color: #999; font-size: 12px;">
            This link will expire in 24 hours.
        </p>

        <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

        <p style="color: #999; font-size: 12px;">
            If you did not register for an account, please ignore this email.
        </p>
    </div>
</body>
</html>
    '''

    try:
        send_mail(
            subject='Confirm your AuctionApp account',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,  # Use settings variable
            recipient_list=[user.email],
            html_message=html_message,  # Optional HTML version
            fail_silently=False,
        )
        return True
    except Exception as e:
        # Log the error (you should set up proper logging)
        print(f"Error sending confirmation email to {user.email}: {e}")
        return False