# ==============================================================================
# File:      api/app/models/game_table.py
# Purpose:   GameTable model. Represents a DM's campaign table that players can
#            join via invite code.
# Callers:   models/__init__.py
# Callees:   SQLAlchemy (db), datetime, string, random
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime
import string
import random


def _generate_invite_code():
    """Generate a 6-character uppercase alphanumeric invite code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=6))


class GameTable(db.Model):
    __tablename__ = 'game_table'

    id = db.Column(db.Integer, primary_key=True)
    owner_user_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                              nullable=False)
    name = db.Column(db.String(100), nullable=False)
    invite_code = db.Column(db.String(6), unique=True, nullable=False,
                            default=_generate_invite_code)
    # Per-table defaults — last session's settings are remembered here so the DM
    # doesn't pick them every time. Page can still override before Start.
    game_type = db.Column(db.String(50), default='Fantasy D&D')
    art_style = db.Column(db.String(50), default='Oil Painting')
    rating = db.Column(db.String(10), default='PG-13')
    # Whether the Display view overlays the AI-generated caption at the
    # bottom of each scene image. Per-table so the DM can pick the vibe.
    show_captions = db.Column(db.Boolean, default=True)
    # Whether the Display shows the small "Daub the Painter is gathering /
    # painting…" status overlay. Per-table.
    show_daub_updates = db.Column(db.Boolean, default=True)
    # Wake word — the oracle's name. When the transcript addresses her by
    # this name (or her title "Daub the Painter" / "the Painter"), the
    # line is treated as a direct DM command rather than passive narrative.
    # Default "Daub" (single-syllable, hard D + B, won't collide with D&D
    # vocabulary); per-table override.
    scryer_name = db.Column(db.String(50), default='Daub')
    # Scene-extract model for sessions on this table. NULL = system default
    # (env SCENE_MODEL_DEFAULT, then hardcoded Haiku fallback). DM can pick
    # Sonnet 4.6 for higher rule-following at ~2x cost, or stay on Haiku 4.5
    # for cost. Stored on the session at start time so mid-session changes
    # don't affect the active run.
    scene_model = db.Column(db.String(80), nullable=True)
    # fal.ai image-gen endpoint (e.g. "fal-ai/recraft-v3", "fal-ai/flux/dev").
    # NULL = system default. Per-table A/B so we can test image models.
    image_model = db.Column(db.String(120), nullable=True)
    # Free-form DM scratchpad: lore, NPC notes, "the king's name is Mort." Fed
    # into the scene-extract system prompt so Claude has world context.
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    # Relationships
    owner = db.relationship('User', backref=db.backref('owned_tables',
                                                       lazy='dynamic'))
    members = db.relationship('TableMember', backref='table',
                              lazy='dynamic', cascade='all, delete-orphan')
    characters = db.relationship('PlayerCharacter', backref='table',
                                 lazy='dynamic')

    def __repr__(self):
        return f'<GameTable {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'owner_user_id': self.owner_user_id,
            'name': self.name,
            'invite_code': self.invite_code,
            'game_type': self.game_type,
            'art_style': self.art_style,
            'rating': self.rating,
            'show_captions': bool(self.show_captions) if self.show_captions is not None else True,
            'show_daub_updates': bool(self.show_daub_updates) if self.show_daub_updates is not None else True,
            'scryer_name': self.scryer_name or 'Daub',
            'scene_model': self.scene_model,
            'image_model': self.image_model,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
