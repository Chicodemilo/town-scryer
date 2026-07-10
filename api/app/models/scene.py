# ==============================================================================
# File:      api/app/models/scene.py
# Purpose:   Scene model. A single generated image within a session, linking
#            the transcript chunk, prompt, and resulting artwork.
# Callers:   models/__init__.py
# Callees:   SQLAlchemy (db), datetime
# Modified:  2026-06-01
# ==============================================================================
from app import db
from datetime import datetime


class Scene(db.Model):
    __tablename__ = 'scene'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'),
                           nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    image_path = db.Column(db.String(500), nullable=True)
    prompt = db.Column(db.Text, nullable=False)
    scene_description = db.Column(db.Text, nullable=True)
    # Short one-line caption for display under the image (storybook view).
    caption = db.Column(db.String(200), nullable=True)
    # Persistent location label (e.g. "forest campsite", "the Yawning Portal").
    # Inherited from the previous scene unless Claude reports a location change.
    location = db.Column(db.String(150), nullable=True)
    # Short 3-5 word chyron-style location label for the DM-facing
    # "new location" ping. Claude generates this alongside the long
    # location string; used by the front-end banner.
    location_label_short = db.Column(db.String(100), nullable=True)
    transcript_chunk = db.Column(db.Text, nullable=True)
    generation_time_ms = db.Column(db.Integer, nullable=True)
    # DM explicitly thumbs-up'd this image. One-shot — decrements
    # quality_score by 15 on first toggle. Stored so we can mark which
    # scenes earned the nod (future use: in-context examples for Claude).
    thumbs_up = db.Column(db.Boolean, default=False)
    # Short snake_case category for the IMAGE's lead subject — used by the
    # server-side duplicate-shot bookkeeping. Claude tags this in the scene
    # response. Examples: broken_wagon_landscape, character_face_closeup,
    # interior_architecture, weather_phenomenon, object_detail.
    subject_category = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Scene {self.id} session={self.session_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'image_url': self.image_url,
            'image_path': self.image_path,
            'prompt': self.prompt,
            'scene_description': self.scene_description,
            'caption': self.caption,
            'location': self.location,
            'location_label_short': self.location_label_short,
            'transcript_chunk': self.transcript_chunk,
            'generation_time_ms': self.generation_time_ms,
            'thumbs_up': bool(self.thumbs_up),
            'subject_category': self.subject_category,
            # 'Z' suffix so browser parses as UTC. Without it, naive ISO
            # strings get interpreted as local time, displaying Scene Feed
            # timestamps hours off (same root cause as the elapsed-timer
            # 00:00 bug).
            'created_at': (self.created_at.isoformat() + 'Z') if self.created_at else None,
        }
