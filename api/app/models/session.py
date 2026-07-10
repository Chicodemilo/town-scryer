# ==============================================================================
# File:      api/app/models/session.py
# Purpose:   Session model. Represents an active Town Scryer session where
#            audio is captured, scenes are generated, and costs are tracked.
# Callers:   models/__init__.py
# Callees:   SQLAlchemy (db), datetime, uuid
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime
import uuid


class Session(db.Model):
    __tablename__ = 'session'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('game_table.id'),
                         nullable=True)
    session_token = db.Column(db.String(36), unique=True, nullable=False,
                              default=lambda: str(uuid.uuid4()))
    last_heartbeat = db.Column(db.DateTime, nullable=False,
                               default=datetime.utcnow)
    status = db.Column(db.Enum('active', 'paused', 'ended',
                               name='session_status'),
                       default='active')
    image_count = db.Column(db.Integer, default=0)
    regen_count = db.Column(db.Integer, default=0)
    api_call_count = db.Column(db.Integer, default=0)
    estimated_cost_cents = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    max_duration_minutes = db.Column(db.Integer, default=480)
    game_type = db.Column(db.String(50), default='fantasy_dnd')
    art_style = db.Column(db.String(50), default='Oil Painting')
    rating = db.Column(db.String(10), default='PG-13')
    # Internal quality signal. Higher = worse run. +20 per DM correction,
    # +10 per regen, -10 per scene naturally accepted (replaced by next).
    quality_score = db.Column(db.Integer, default=0)
    # Snapshot of which Claude model handled scene extraction for this
    # session. Set at start time from table.scene_model (or system default)
    # so changing the table picker mid-session doesn't break the A/B.
    scene_model = db.Column(db.String(80), nullable=True)
    # Snapshot of which fal image-gen endpoint this session used. Same
    # pattern as scene_model — locked at start, doesn't change mid-run.
    image_model = db.Column(db.String(120), nullable=True)
    # Timestamp of the last user-triggered "Change Image" call. Used to
    # enforce a 30-second cooldown so the DM can't spam-mash the button.
    last_change_image_at = db.Column(db.DateTime, nullable=True)
    # Set when image generation starts (fal call in flight), cleared when
    # the Scene record is persisted. The Display polls this to know
    # whether to show "Daub is gathering…" or "Daub is painting…".
    generation_started_at = db.Column(db.DateTime, nullable=True)
    # Rolling transcript buffer — every Whisper output gets appended here
    # (trimmed to last ~5000 chars). Used by regen / Make-A-New-Image so
    # they re-interpret from FRESH context, not the audio that triggered
    # the last scene N minutes ago.
    transcript_buffer = db.Column(db.Text, nullable=True)
    # Counts how many times the vision audit ran (gated on quality_score
    # crossing threshold) and how many times it triggered a retry.
    audit_count = db.Column(db.Integer, default=0)
    audit_retry_count = db.Column(db.Integer, default=0)
    # Hard duplicate-shot check counters. Vision compare against previous
    # image, gated on subject_category repeating in last 2 scenes. Capped
    # at 3 retries per session to bound cost on a stubborn Recraft attractor.
    dupe_check_count = db.Column(db.Integer, default=0)
    dupe_retry_count = db.Column(db.Integer, default=0)
    # Movie-poster backdrop generated at session start. Shown on the
    # Display title card behind the campaign name + tags + party listing.
    title_card_image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('sessions', lazy='dynamic'))
    game_table = db.relationship('GameTable', backref=db.backref('sessions',
                                                                  lazy='dynamic'))
    scenes = db.relationship('Scene', backref='session', lazy='dynamic',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Session {self.session_token}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'table_id': self.table_id,
            'session_token': self.session_token,
            # Timestamps are emitted as UTC ISO with explicit 'Z' suffix so
            # browser `new Date()` doesn't parse them as local time and put
            # the session start in the future (which clamps the elapsed
            # timer to 00:00).
            'last_heartbeat': (self.last_heartbeat.isoformat() + 'Z') if self.last_heartbeat else None,
            'status': self.status,
            'image_count': self.image_count,
            'regen_count': self.regen_count,
            'api_call_count': self.api_call_count,
            'estimated_cost_cents': self.estimated_cost_cents,
            'started_at': (self.started_at.isoformat() + 'Z') if self.started_at else None,
            'ended_at': (self.ended_at.isoformat() + 'Z') if self.ended_at else None,
            'max_duration_minutes': self.max_duration_minutes,
            'game_type': self.game_type,
            'art_style': self.art_style,
            'rating': self.rating,
            'quality_score': self.quality_score or 0,
            'scene_model': self.scene_model,
            'image_model': self.image_model,
            'audit_count': self.audit_count or 0,
            'audit_retry_count': self.audit_retry_count or 0,
            'dupe_check_count': self.dupe_check_count or 0,
            'dupe_retry_count': self.dupe_retry_count or 0,
            'title_card_image_url': self.title_card_image_url,
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
            'updated_at': (self.updated_at.isoformat() + 'Z') if self.updated_at else None,
        }
