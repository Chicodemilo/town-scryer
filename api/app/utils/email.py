# ==============================================================================
# File:      api/app/utils/email.py
# Purpose:   Email sending utilities. Provides functions for verification,
#            email change confirmation, and admin user invites. Falls back
#            to console logging when SMTP is not configured.
# Callers:   auth_service.py
# Callees:   smtplib, os, logging, email.mime
# Modified:  2026-06-01
# ==============================================================================
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def _get_smtp_config():
    app_name = os.getenv('APP_NAME', 'Town Scryer')
    return {
        'host': os.getenv('SMTP_HOST'),
        'user': os.getenv('SMTP_USER'),
        'password': os.getenv('SMTP_PASSWORD'),
        'port': int(os.getenv('SMTP_PORT', '587')),
        'from_email': os.getenv('SMTP_FROM_EMAIL', os.getenv('SMTP_USER') or f'noreply@{app_name.lower().replace(" ", "")}.com'),
        'app_name': app_name,
        'frontend_url': os.getenv('FRONTEND_URL', 'http://localhost:3151'),
    }


def _send_or_log(to_email, subject, html_body, dev_label, dev_extra=''):
    cfg = _get_smtp_config()
    if not cfg['host'] or not cfg['user'] or not cfg['password']:
        logger.info("=" * 60)
        logger.info(f"  {dev_label} (Dev Mode — No SMTP configured)")
        logger.info(f"  To: {to_email}")
        logger.info(f"  Subject: {subject}")
        if dev_extra:
            logger.info(f"  {dev_extra}")
        logger.info("=" * 60)
        print("\n" + "=" * 60)
        print(f"  {dev_label} (Dev Mode)")
        print(f"  To: {to_email}")
        if dev_extra:
            print(f"  {dev_extra}")
        print("=" * 60 + "\n")
        return True

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = cfg['from_email']
        msg['To'] = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(cfg['host'], cfg['port']) as server:
            server.starttls()
            server.login(cfg['user'], cfg['password'])
            server.sendmail(cfg['from_email'], to_email, msg.as_string())

        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_verification_email(to_email, token, username):
    """Send verification email. Falls back to console logging if SMTP is not configured."""
    cfg = _get_smtp_config()
    verify_url = f"{cfg['frontend_url']}/verify-email?token={token}"
    subject = f"Verify your email — {cfg['app_name']}"
    html_body = f"""
    <h2>Welcome to {cfg['app_name']}, {username}!</h2>
    <p>Please verify your email address by clicking the link below:</p>
    <p><a href="{verify_url}">Verify Email</a></p>
    <p>Or copy this URL into your browser:</p>
    <p>{verify_url}</p>
    """
    return _send_or_log(to_email, subject, html_body, 'EMAIL VERIFICATION', f'Verify URL: {verify_url}')


def send_email_change_verification(to_email, token, username):
    """Send email change verification to the new email address."""
    cfg = _get_smtp_config()
    verify_url = f"{cfg['frontend_url']}/verify-email?token={token}&type=email-change"
    subject = f"Confirm your new email — {cfg['app_name']}"
    html_body = f"""
    <h2>Email Change Request — {cfg['app_name']}</h2>
    <p>Hi {username}, you requested to change your email to this address.</p>
    <p>Click the link below to confirm:</p>
    <p><a href="{verify_url}">Confirm New Email</a></p>
    <p>Or copy this URL: {verify_url}</p>
    <p>If you didn't request this, please ignore this email.</p>
    """
    return _send_or_log(to_email, subject, html_body, 'EMAIL CHANGE VERIFICATION', f'Verify URL: {verify_url}')


def send_invite_email(to_email, token):
    """Send invite email to a new user."""
    cfg = _get_smtp_config()
    invite_url = f"{cfg['frontend_url']}/invite?token={token}"
    subject = f"You're invited to {cfg['app_name']}"
    html_body = f"""
    <h2>You've been invited to {cfg['app_name']}!</h2>
    <p>An administrator has invited you to join. Click below to create your account:</p>
    <p><a href="{invite_url}">Accept Invite</a></p>
    <p>Or copy this URL: {invite_url}</p>
    """
    return _send_or_log(to_email, subject, html_body, 'USER INVITE', f'Invite URL: {invite_url}')
