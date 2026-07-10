# ==============================================================================
# File:      api/app/models/user.py
# Purpose:   User account model. Handles authentication fields, email
#            verification, avatar, and admin permissions.
# Callers:   auth_service.py, routes/auth.py, routes/admin.py,
#            routes/uploads.py, models/__init__.py
# Callees:   SQLAlchemy (db), secrets, datetime, json,
#            werkzeug.security, sqlalchemy.event
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import event
import secrets
import json


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_token = db.Column(db.String(255), nullable=True)
    verification_sent_at = db.Column(db.DateTime, nullable=True)
    # Terms & Conditions
    terms_accepted = db.Column(db.Boolean, default=False, nullable=False)
    terms_accepted_at = db.Column(db.DateTime, nullable=True)
    # Email change (pending until verified)
    pending_email = db.Column(db.String(100), nullable=True)
    pending_email_token = db.Column(db.String(255), nullable=True)
    # Admin invite
    invite_token = db.Column(db.String(255), nullable=True)
    invited_by = db.Column(db.Integer, nullable=True)
    # Admin section permissions (JSON string)
    admin_permissions = db.Column(db.Text, nullable=True)
    # Avatar
    avatar = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    deactivated_at = db.Column(db.DateTime, nullable=True)
    # Usage tracking
    monthly_image_count = db.Column(db.Integer, default=0)
    monthly_session_count = db.Column(db.Integer, default=0)
    monthly_image_reset_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def check_password(self, password):
        return self.password_hash == password or check_password_hash(self.password_hash, password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def generate_verification_token(self):
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_sent_at = datetime.utcnow()
        return self.verification_token

    def generate_pending_email_token(self):
        self.pending_email_token = secrets.token_urlsafe(32)
        return self.pending_email_token

    def generate_invite_token(self):
        self.invite_token = secrets.token_urlsafe(32)
        return self.invite_token

    def get_admin_permissions(self):
        if not self.admin_permissions:
            return {}
        try:
            return json.loads(self.admin_permissions)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_admin_permissions(self, perms):
        self.admin_permissions = json.dumps(perms)

    def has_admin_section(self, section):
        if not self.is_admin:
            return False
        perms = self.get_admin_permissions()
        if not perms:
            return True  # No restrictions set = full access
        return perms.get(section, False)

    def to_dict(self):
        d = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_admin': self.is_admin,
            'email_verified': self.email_verified,
            'terms_accepted': self.terms_accepted,
            'terms_accepted_at': self.terms_accepted_at.isoformat() if self.terms_accepted_at else None,
            'pending_email': self.pending_email,
            'admin_permissions': self.get_admin_permissions(),
            'avatar': self.avatar,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'deactivated_at': self.deactivated_at.isoformat() if self.deactivated_at else None,
            'monthly_image_count': self.monthly_image_count,
            'monthly_session_count': self.monthly_session_count,
            'monthly_image_reset_date': self.monthly_image_reset_date.isoformat() if self.monthly_image_reset_date else None,
        }
        return d
