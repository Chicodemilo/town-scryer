# ==============================================================================
# File:      api/app/services/session_service.py
# Purpose:   Session management service. Handles starting, pausing, resuming,
#            ending sessions, heartbeat updates, stale-session detection, and
#            latest-scene retrieval.
# Callers:   routes/sessions.py
# Callees:   models/session.py, models/scene.py, models/user_preferences.py,
#            SQLAlchemy (db), datetime, uuid
# Modified:  2026-06-01
# ==============================================================================
from app import db
from app.models.session import Session
from app.models.scene import Scene
from app.models.user_preferences import UserPreferences
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)

STALE_HEARTBEAT_MINUTES = 3


class SessionService:
    """Handles session lifecycle: start, pause, resume, end, heartbeat."""

    @staticmethod
    def _is_stale(session):
        """Return True if the session's last heartbeat is older than 3 minutes."""
        if not session.last_heartbeat:
            return True
        return datetime.utcnow() - session.last_heartbeat > timedelta(
            minutes=STALE_HEARTBEAT_MINUTES
        )

    @staticmethod
    def _auto_pause_if_stale(session):
        """Auto-pause a session if its heartbeat is stale. Returns True if paused."""
        if session.status == 'active' and SessionService._is_stale(session):
            session.status = 'paused'
            db.session.commit()
            logger.info(f"Auto-paused stale session {session.session_token}")
            return True
        return False

    @staticmethod
    def get_active_session(user_id):
        """Return the user's active or paused session, or None."""
        session = Session.query.filter_by(
            user_id=user_id
        ).filter(
            Session.status.in_(['active', 'paused'])
        ).first()
        if session:
            SessionService._auto_pause_if_stale(session)
        return session

    @staticmethod
    def start_session(user_id, game_type=None, art_style=None, rating=None,
                      table_id=None, show_captions=None):
        """Start a new session. Returns (session, error_message)."""
        existing = Session.query.filter_by(
            user_id=user_id, status='active'
        ).first()
        if existing:
            if SessionService._is_stale(existing):
                existing.status = 'paused'
                db.session.commit()
                logger.info(
                    f"Auto-paused stale session {existing.session_token} "
                    f"before starting new one"
                )
            else:
                return None, 'You already have an active session'

        # Also check for paused sessions -- a paused session is fine, user can
        # start a new one (the old paused one stays paused).

        # Resolve defaults from UserPreferences or hardcoded
        prefs = UserPreferences.query.filter_by(user_id=user_id).first()
        if game_type is None:
            game_type = prefs.game_type if prefs else 'fantasy_dnd'
        if art_style is None:
            art_style = prefs.art_style if prefs else 'Oil Painting'
        if rating is None:
            rating = prefs.rating if prefs else 'PG-13'

        now = datetime.utcnow()
        session = Session(
            user_id=user_id,
            table_id=table_id,
            status='active',
            started_at=now,
            last_heartbeat=now,
            game_type=game_type,
            art_style=art_style,
            rating=rating,
        )
        db.session.add(session)

        # Per-table memory: persist these settings on the linked table so the
        # DM doesn't re-pick them next session. The form on /session still lets
        # the DM override before clicking Start.
        table_name = None
        if table_id:
            from app.models.game_table import GameTable
            table = GameTable.query.get(table_id)
            if table:
                table.game_type = game_type
                table.art_style = art_style
                table.rating = rating
                if show_captions is not None:
                    table.show_captions = bool(show_captions)
                table_name = table.name
                # Snapshot the table's scene_model onto the session so the
                # active run is locked to a single model for clean A/B.
                if table.scene_model:
                    session.scene_model = table.scene_model
                if table.image_model:
                    session.image_model = table.image_model
        # Fall back to system defaults if no per-table choice
        if not session.scene_model:
            session.scene_model = os.getenv(
                'SCENE_MODEL_DEFAULT', 'claude-haiku-4-5-20251001'
            )
        if not session.image_model:
            session.image_model = os.getenv(
                'IMAGE_MODEL_DEFAULT', 'fal-ai/recraft-v3'
            )

        # Movie-poster backdrop for the title card. Sync so it's ready by
        # the time the DM opens the Display. ~5-10s added to session start;
        # acceptable since pre-game banter buys us the entire wait.
        from app.services.image_gen import generate_title_card
        try:
            session.title_card_image_url = generate_title_card(session, table_name)
        except Exception:
            logger.exception('Title card pre-render failed; continuing')

        db.session.commit()
        logger.info(f"Session started: {session.session_token} for user {user_id}")
        return session, None

    @staticmethod
    def get_session_for_user(user_id, session_token):
        """Fetch a session by token, verifying it belongs to the user.
        Returns (session, error_message)."""
        session = Session.query.filter_by(
            session_token=session_token, user_id=user_id
        ).first()
        if not session:
            return None, 'Session not found'
        SessionService._auto_pause_if_stale(session)
        return session, None

    @staticmethod
    def pause_session(user_id, session_token):
        session, error = SessionService.get_session_for_user(user_id, session_token)
        if error:
            return None, error
        if session.status != 'active':
            return None, f'Session is not active (current status: {session.status})'
        session.status = 'paused'
        db.session.commit()
        return session, None

    @staticmethod
    def resume_session(user_id, session_token):
        session, error = SessionService.get_session_for_user(user_id, session_token)
        if error:
            return None, error
        if session.status != 'paused':
            return None, f'Session is not paused (current status: {session.status})'
        session.status = 'active'
        session.last_heartbeat = datetime.utcnow()
        db.session.commit()
        return session, None

    @staticmethod
    def end_session(user_id, session_token):
        session, error = SessionService.get_session_for_user(user_id, session_token)
        if error:
            return None, error
        if session.status == 'ended':
            return None, 'Session is already ended'
        now = datetime.utcnow()
        session.status = 'ended'
        session.ended_at = now
        db.session.commit()

        duration_seconds = int(
            (session.ended_at - session.started_at).total_seconds()
        )
        return session, None

    @staticmethod
    def heartbeat(user_id, session_token):
        session, error = SessionService.get_session_for_user(user_id, session_token)
        if error:
            return None, error
        if session.status != 'active':
            return None, f'Session is not active (current status: {session.status})'
        session.last_heartbeat = datetime.utcnow()
        db.session.commit()
        return session, None

    @staticmethod
    def get_latest_scene(user_id):
        """Return the most recent Scene for the user's active session, or None."""
        session = Session.query.filter_by(
            user_id=user_id
        ).filter(
            Session.status.in_(['active', 'paused'])
        ).first()
        if not session:
            return None, 'No active session'
        scene = Scene.query.filter_by(
            session_id=session.id
        ).order_by(Scene.created_at.desc()).first()
        return scene, None
