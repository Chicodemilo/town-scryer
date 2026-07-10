# ==============================================================================
# File:      api/app/models/session_correction.py
# Purpose:   SessionCorrection model. Stores DM-submitted text corrections that
#            override transcript interpretation during scene analysis.
# Callers:   models/__init__.py, routes/sessions.py, services/scene_service.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime


class SessionCorrection(db.Model):
    __tablename__ = 'session_correction'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'),
                           nullable=False)
    text = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    session = db.relationship('Session',
                              backref=db.backref('corrections', lazy='dynamic'))

    def __repr__(self):
        return f'<SessionCorrection {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'text': self.text,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
