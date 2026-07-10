# ==============================================================================
# File:      api/app/models/npc.py
# Purpose:   NPC model. A recurring non-player character tied to a game table.
#            Surfaces to Claude in the scene-extract system prompt so NPCs
#            stay visually consistent across sessions.
# Callers:   models/__init__.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-06-05
# ==============================================================================
from app import db
from datetime import datetime


class Npc(db.Model):
    __tablename__ = 'npc'

    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.Integer, db.ForeignKey('game_table.id'),
                         nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    portrait_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Npc {self.name} table={self.table_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'table_id': self.table_id,
            'name': self.name,
            'description': self.description,
            'portrait_path': self.portrait_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
