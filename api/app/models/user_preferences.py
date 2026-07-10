# ==============================================================================
# File:      api/app/models/user_preferences.py
# Purpose:   UserPreferences model. Stores per-user default settings for
#            game type, art style, and gore level.
# Callers:   models/__init__.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime


class UserPreferences(db.Model):
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True,
                        nullable=False)
    game_type = db.Column(db.String(50), default='fantasy_dnd')
    art_style = db.Column(db.String(50), default='Oil Painting')
    rating = db.Column(db.String(10), default='PG-13')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('preferences',
                                                      uselist=False))

    def __repr__(self):
        return f'<UserPreferences user_id={self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'game_type': self.game_type,
            'art_style': self.art_style,
            'rating': self.rating,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
