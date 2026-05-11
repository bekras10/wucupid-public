import os
import logging
from flask_mail import Mail, Message
from flask import current_app, url_for

mail = Mail()
logger = logging.getLogger(__name__)


def _is_truthy_env(var_name: str) -> bool:
    """Return True if the environment variable is a truthy value."""
    return os.environ.get(var_name, '').strip().lower() in {'1', 'true', 'on', 'yes'}


def _match_emails_disabled() -> bool:
    """Global kill switch for match-related emails."""
    return _is_truthy_env('DISABLE_OUTBOUND_EMAILS') or _is_truthy_env('DISABLE_MATCH_EMAILS')

def send_verification_email(to_email, token):
    verification_url = url_for('auth.verify_email', token=token, _external=True, _scheme='https').replace('wucupidbackend.onrender.com', 'api.wucupid.com') + '?redirect_to=https://wucupid.com'
    
    # Check if FLASK_ENV is development
    is_dev = os.environ.get('FLASK_ENV') == 'development'
    
    # Log whether we're in dev or production
    logger.info(f"Email sending mode: {'DEVELOPMENT' if is_dev else 'PRODUCTION'}")
    logger.info(f"Verification URL: {verification_url}")
    
    try:
        # Always print the verification URL in logs for debugging
        logger.info(f"Generated verification URL: {verification_url}")
        
        # If in dev mode or testing, we might skip sending the actual email
        if is_dev and os.environ.get('SKIP_EMAIL_SEND') == 'true':
            logger.info(f"DEVELOPMENT: Skipping actual email send to {to_email}")
            return True, verification_url
        
        # Attempt to send the real email
        msg = Message(
            'Verify your WUCUPID account',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )
        
        msg.body = f'''Please verify your WUCUPID account by clicking the link below:
        
{verification_url}

If you did not register for WUCUPID, please ignore this email.
'''
        
        logger.info(f"Attempting to send verification email to {to_email}")
        mail.send(msg)
        logger.info(f"Successfully sent verification email to {to_email}")
        
        # Include URL in return even in production, but frontend will hide it
        return True, verification_url
    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
        # For development, we'll just print the verification URL
        logger.info(f"DEVELOPMENT MODE: Verification URL: {verification_url}")
        # Return as tuple (success, url)
        return False, verification_url

def send_password_reset_email(to_email, token):
    reset_url = f"https://wucupid.com/auth/reset-password?token={token}"
    
    # Check if FLASK_ENV is development
    is_dev = os.environ.get('FLASK_ENV') == 'development'
    
    # Log whether we're in dev or production
    logger.info(f"Password reset email mode: {'DEVELOPMENT' if is_dev else 'PRODUCTION'}")
    logger.info(f"Reset URL: {reset_url}")
    
    try:
        # Always print the reset URL in logs for debugging
        logger.info(f"Generated password reset URL: {reset_url}")
        
        # If in dev mode or testing, we might skip sending the actual email
        if is_dev and os.environ.get('SKIP_EMAIL_SEND') == 'true':
            logger.info(f"DEVELOPMENT: Skipping actual email send to {to_email}")
            return True
        
        # Attempt to send the real email
        msg = Message(
            'Reset your WUCUPID password',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )
        
        msg.body = f'''We received a request to reset your WUCUPID password.

Click the link below to reset your password:

{reset_url}

This link will expire in 1 hour.

If you did not request a password reset, please ignore this email.
'''
        
        logger.info(f"Attempting to send password reset email to {to_email}")
        mail.send(msg)
        logger.info(f"Successfully sent password reset email to {to_email}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email to {to_email}: {str(e)}")
        logger.info(f"DEVELOPMENT MODE: Reset URL: {reset_url}")
        return False

def send_matches_available_email(to_email, cycle_number):
    matches_url = "https://wucupid.com/matches"
    
    # Check if FLASK_ENV is development
    is_dev = os.environ.get('FLASK_ENV') == 'development'
    
    # Emergency kill switch for match emails
    if _match_emails_disabled():
        logger.warning(f"Match emails disabled via env; skipping send to {to_email}")
        return True
    
    # Log whether we're in dev or production
    logger.info(f"Matches notification email mode: {'DEVELOPMENT' if is_dev else 'PRODUCTION'}")
    logger.info(f"Matches URL: {matches_url}")
    
    try:
        # Always print the matches URL in logs for debugging
        logger.info(f"Sending matches available notification to: {to_email}")
        
        # If in dev mode or testing, we might skip sending the actual email
        if is_dev and os.environ.get('SKIP_EMAIL_SEND') == 'true':
            logger.info(f"DEVELOPMENT: Skipping actual email send to {to_email}")
            return True
        
        # Attempt to send the real email
        msg = Message(
            'Your WUCUPID matches are ready! 💕',
            sender=current_app.config['MAIL_DEFAULT_SENDER'],
            recipients=[to_email]
        )
        
        msg.body = f'''Great news! Your WUCUPID matches for this cycle are now available.

Log in and visit your dashboard to see your matches:

https://wucupid.com/auth/login

Don't wait too long - matches are only available for a limited time before the next cycle begins!

Good luck and happy matching! 💕

The WUCUPID Team
'''
        
        logger.info(f"Attempting to send matches notification email to {to_email}")
        mail.send(msg)
        logger.info(f"Successfully sent matches notification email to {to_email}")
        
        return True
    except Exception as e:
        logger.error(f"Failed to send matches notification email to {to_email}: {str(e)}")
        logger.info(f"DEVELOPMENT MODE: Matches URL: {matches_url}")
        return False

def send_matches_available_emails_bulk(user_emails, cycle_number):
    """Send matches available emails to multiple users"""
    success_count = 0
    failure_count = 0
    
    logger.info(f"Sending matches available notifications to {len(user_emails)} users for cycle #{cycle_number}")
    
    # Global kill switch for safety
    if _match_emails_disabled():
        logger.warning("Match emails disabled via env; skipping bulk send")
        return success_count, failure_count
    
    for email in user_emails:
        try:
            if send_matches_available_email(email, cycle_number):
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            logger.error(f"Error sending match notification to {email}: {str(e)}")
            failure_count += 1
    
    logger.info(f"Match notifications sent: {success_count} successful, {failure_count} failed")
    return success_count, failure_count 