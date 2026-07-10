# ==============================================================================
# File:      api/app/services/auth_service.py
# Purpose:   Authentication and user management service. Handles
#            registration, login, email verification/change, admin seeding,
#            terms acceptance, admin invites, and permission management.
# Callers:   routes/auth.py, routes/admin.py, app/__init__.py,
#            services/__init__.py
# Callees:   models/user.py, models/terms_content.py, utils/email.py,
#            SQLAlchemy (db), werkzeug.security, datetime, logging
# Modified:  2026-06-01
# ==============================================================================
from app import db
from app.models.user import User
from app.models.terms_content import TermsContent
from app.utils.email import send_verification_email, send_email_change_verification, send_invite_email
from werkzeug.security import generate_password_hash
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Handles user registration, authentication, verification, and admin seeding"""

    @staticmethod
    def register(username, email, password):
        if User.query.filter_by(username=username).first():
            return None, 'Username already taken'
        if User.query.filter_by(email=email).first():
            return None, 'Email already registered'

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        token = user.generate_verification_token()
        db.session.add(user)
        db.session.commit()

        send_verification_email(email, token, username)

        logger.info(f"New user registered: {username}")
        return user, None

    @staticmethod
    def verify_email(token):
        if not token:
            return None, 'Verification token required'
        user = User.query.filter_by(verification_token=token).first()
        if not user:
            return None, 'Invalid verification token'
        user.email_verified = True
        user.verification_token = None
        db.session.commit()
        logger.info(f"Email verified for user: {user.username}")
        return user, None

    @staticmethod
    def resend_verification(user_id):
        user = User.query.get(user_id)
        if not user:
            return None, 'User not found'
        if user.email_verified:
            return None, 'Email already verified'
        token = user.generate_verification_token()
        db.session.commit()
        send_verification_email(user.email, token, user.username)
        return user, None

    @staticmethod
    def authenticate(username, password):
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        if user and user.check_password(password):
            logger.info(f"Successful login for user: {user.username}")
            return user
        return None

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.get(user_id)

    @staticmethod
    def seed_admin(username, email, password):
        existing = User.query.filter_by(is_admin=True).first()
        if existing:
            logger.info(f"Admin user already exists: {existing.username}")
            return existing

        admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=True,
            email_verified=True,
            terms_accepted=True,
            terms_accepted_at=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()
        logger.info(f"Admin user created: {username}")
        return admin

    # --- Terms & Conditions ---

    @staticmethod
    def accept_terms(user_id):
        user = User.query.get(user_id)
        if not user:
            return None, 'User not found'
        user.terms_accepted = True
        user.terms_accepted_at = datetime.utcnow()
        db.session.commit()
        return user, None

    @staticmethod
    def get_terms():
        terms = TermsContent.query.order_by(TermsContent.id.desc()).first()
        if not terms:
            terms = TermsContent(
                content='These are the placeholder terms and conditions for this application. The administrator can update these at any time from the admin panel.',
                version=1
            )
            db.session.add(terms)
            db.session.commit()
        return terms

    @staticmethod
    def update_terms(content, admin_user_id):
        terms = TermsContent.query.order_by(TermsContent.id.desc()).first()
        if terms:
            terms.content = content
            terms.version = terms.version + 1
            terms.updated_by = admin_user_id
            terms.updated_at = datetime.utcnow()
        else:
            terms = TermsContent(content=content, version=1, updated_by=admin_user_id)
            db.session.add(terms)
        db.session.commit()
        return terms

    @staticmethod
    def reset_all_terms():
        User.query.update({User.terms_accepted: False, User.terms_accepted_at: None})
        db.session.commit()
        return True

    # --- Email Change ---

    @staticmethod
    def change_email(user_id, new_email):
        user = User.query.get(user_id)
        if not user:
            return None, 'User not found'
        if new_email == user.email:
            return None, 'New email is the same as current email'
        existing = User.query.filter_by(email=new_email).first()
        if existing:
            return None, 'Email already in use'
        user.pending_email = new_email
        token = user.generate_pending_email_token()
        db.session.commit()
        send_email_change_verification(new_email, token, user.username)
        return user, None

    @staticmethod
    def verify_new_email(token):
        if not token:
            return None, 'Token required'
        user = User.query.filter_by(pending_email_token=token).first()
        if not user:
            return None, 'Invalid or expired token'
        user.email = user.pending_email
        user.pending_email = None
        user.pending_email_token = None
        db.session.commit()
        logger.info(f"Email changed for user: {user.username} to {user.email}")
        return user, None

    # --- Admin Invite ---

    @staticmethod
    def invite_user(email, invited_by_id):
        existing = User.query.filter_by(email=email).first()
        if existing:
            return None, 'A user with this email already exists'
        user = User(
            username=email.split('@')[0],
            email=email,
            password_hash='__INVITE_PENDING__',
            invite_token=None,
            invited_by=invited_by_id,
        )
        token = user.generate_invite_token()
        db.session.add(user)
        db.session.commit()
        send_invite_email(email, token)
        logger.info(f"Invite sent to {email} by admin {invited_by_id}")
        return user, None

    @staticmethod
    def complete_invite(token, username, password):
        if not token:
            return None, 'Invite token required'
        user = User.query.filter_by(invite_token=token).first()
        if not user:
            return None, 'Invalid or expired invite token'
        # Check username availability if they're changing it
        if username != user.username:
            existing = User.query.filter_by(username=username).first()
            if existing:
                return None, 'Username already taken'
        user.username = username
        user.set_password(password)
        user.invite_token = None
        user.email_verified = True
        db.session.commit()
        logger.info(f"Invite completed for user: {user.username}")
        return user, None

    # --- Admin Permissions ---

    @staticmethod
    def update_admin_permissions(user_id, permissions):
        user = User.query.get(user_id)
        if not user:
            return None, 'User not found'
        if not user.is_admin:
            return None, 'User is not an admin'
        user.set_admin_permissions(permissions)
        db.session.commit()
        return user, None

    @staticmethod
    def get_admin_users():
        return User.query.filter_by(is_admin=True).all()
