# ==============================================================================
# File:      api/app/models/page_hit.py
# Purpose:   PageHit model for page hit tracking. Records path, IP address,
#            referrer, and user agent for analytics.
# Callers:   routes/admin.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-04-22
# ==============================================================================
from app import db
from datetime import datetime


class PageHit(db.Model):
    """A single page view hit for analytics tracking."""
    __tablename__ = 'page_hit'

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(255), nullable=False)
    ip_address = db.Column(db.String(45))
    referrer = db.Column(db.String(500))
    user_agent = db.Column(db.String(500))
    blocked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'path': self.path,
            'ip_address': self.ip_address,
            'referrer': self.referrer,
            'user_agent': self.user_agent,
            'blocked': self.blocked,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
