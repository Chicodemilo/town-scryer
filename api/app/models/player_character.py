# ==============================================================================
# File:      api/app/models/player_character.py
# Purpose:   PlayerCharacter model. Stores a user's named character with an
#            optional description and portrait for session personalization.
# Callers:   models/__init__.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime


class PlayerCharacter(db.Model):
    __tablename__ = 'player_character'

    id = db.Column(db.Integer, primary_key=True)
    # user_id is nullable so a DM can pre-create characters that a player later claims.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    table_id = db.Column(db.Integer, db.ForeignKey('game_table.id'),
                         nullable=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    portrait_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    # Unique constraint: one character per user per table
    __table_args__ = (
        db.UniqueConstraint('user_id', 'table_id', name='uq_user_table_char'),
    )

    # Relationships
    user = db.relationship('User', backref=db.backref('player_characters',
                                                      lazy='dynamic'))

    def __repr__(self):
        return f'<PlayerCharacter {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'claimed_by_username': self.user.username if self.user_id and self.user else None,
            'table_id': self.table_id,
            'name': self.name,
            'description': self.description,
            'portrait_path': self.portrait_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
