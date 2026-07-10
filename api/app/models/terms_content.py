# ==============================================================================
# File:      api/app/models/terms_content.py
# Purpose:   TermsContent model. Stores the current Terms & Conditions
#            text with versioning. Updated by admins via auth_service.
# Callers:   auth_service.py, models/__init__.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-04-22
# ==============================================================================
from app import db
from datetime import datetime


class TermsContent(db.Model):
    __tablename__ = 'terms_content'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    updated_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'version': self.version,
            'updated_by': self.updated_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
