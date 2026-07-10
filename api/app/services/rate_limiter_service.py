# ==============================================================================
# File:      api/app/services/rate_limiter_service.py
# Purpose:   Session rate-limit and cost enforcement. Provides checks for the
#            chunk endpoint (cooldown, image cap, duration, cost) and session
#            start (monthly caps, monthly reset).
# Callers:   routes/sessions.py
# Callees:   models/session.py, models/scene.py, models/user.py,
#            SQLAlchemy (db), datetime
# Modified:  2026-06-01
# ==============================================================================
from app import db
from app.models.scene import Scene
from app.models.user import User
from datetime import datetime, timedelta, date
import logging

logger = logging.getLogger(__name__)

# Chunk-level limits
IMAGE_COOLDOWN_SECONDS = 90
SESSION_IMAGE_CAP = 120
SESSION_MAX_DURATION_MINUTES = 480
SESSION_COST_LIMIT_CENTS = 500

# Monthly limits
MONTHLY_IMAGE_CAP = 500
MONTHLY_SESSION_CAP = 30
MONTHLY_RESET_DAYS = 30


class RateLimiterService:
    """Enforces rate limits and cost caps on sessions and users."""

    # ------------------------------------------------------------------
    # Chunk-level checks (called before image generation)
    # ------------------------------------------------------------------

    @staticmethod
    def check_image_cooldown(session):
        """Return a skip dict if the last scene was created less than 90s ago,
        or None if the cooldown has passed."""
        last_scene = (
            Scene.query
            .filter_by(session_id=session.id)
            .order_by(Scene.created_at.desc())
            .first()
        )
        if last_scene and last_scene.created_at:
            elapsed = (datetime.utcnow() - last_scene.created_at).total_seconds()
            if elapsed < IMAGE_COOLDOWN_SECONDS:
                return {'image_skipped': True, 'reason': 'cooldown'}
        return None

    @staticmethod
    def check_session_image_cap(session):
        """Return a force-pause dict if session has hit the image cap,
        or None if under the cap."""
        if (session.image_count or 0) >= SESSION_IMAGE_CAP:
            session.status = 'paused'
            db.session.commit()
            return {'force_paused': True, 'reason': 'session_image_limit'}
        return None

    @staticmethod
    def check_session_duration(session):
        """Return a force-pause dict if session exceeds the duration limit,
        or None if within the limit."""
        if session.started_at:
            elapsed_minutes = (
                datetime.utcnow() - session.started_at
            ).total_seconds() / 60
            if elapsed_minutes >= SESSION_MAX_DURATION_MINUTES:
                session.status = 'paused'
                db.session.commit()
                return {'force_paused': True, 'reason': 'max_duration'}
        return None

    @staticmethod
    def check_cost_limit(session):
        """Return a force-pause dict if session cost exceeds $5,
        or None if under the limit."""
        if (session.estimated_cost_cents or 0) >= SESSION_COST_LIMIT_CENTS:
            session.status = 'paused'
            db.session.commit()
            return {'force_paused': True, 'reason': 'cost_limit'}
        return None

    @staticmethod
    def check_chunk_limits(session):
        """Run all chunk-level checks. Returns a dict to merge into the
        response if any limit is hit, or None if all clear."""
        # Order matters: force-pause checks first, then cooldown
        for check in (
            RateLimiterService.check_session_image_cap,
            RateLimiterService.check_session_duration,
            RateLimiterService.check_cost_limit,
        ):
            result = check(session)
            if result:
                return result

        cooldown = RateLimiterService.check_image_cooldown(session)
        if cooldown:
            return cooldown

        return None

    # ------------------------------------------------------------------
    # Session-start checks
    # ------------------------------------------------------------------

    @staticmethod
    def _reset_monthly_if_needed(user):
        """Reset monthly counters if the reset date is in the past or NULL."""
        today = date.today()
        if user.monthly_image_reset_date is None or user.monthly_image_reset_date <= today:
            user.monthly_image_count = 0
            user.monthly_session_count = 0
            user.monthly_image_reset_date = today + timedelta(days=MONTHLY_RESET_DAYS)
            db.session.commit()
            logger.info(
                f"Monthly counters reset for user {user.id}, "
                f"next reset: {user.monthly_image_reset_date}"
            )

    @staticmethod
    def check_session_start_limits(user_id):
        """Run monthly checks before starting a session.

        Returns (None, None) if all clear, or (error_message, http_status) if
        a limit is hit.
        """
        user = User.query.get(user_id)
        if not user:
            return 'User not found', 404

        # Reset monthly counters if needed
        RateLimiterService._reset_monthly_if_needed(user)

        if (user.monthly_image_count or 0) >= MONTHLY_IMAGE_CAP:
            return (
                f'Monthly image limit reached ({MONTHLY_IMAGE_CAP}). '
                f'Resets on {user.monthly_image_reset_date}.',
                429,
            )

        if (user.monthly_session_count or 0) >= MONTHLY_SESSION_CAP:
            return (
                f'Monthly session limit reached ({MONTHLY_SESSION_CAP}). '
                f'Resets on {user.monthly_image_reset_date}.',
                429,
            )

        return None, None

    @staticmethod
    def increment_monthly_session_count(user_id):
        """Increment the user's monthly session counter after a successful start."""
        user = User.query.get(user_id)
        if user:
            user.monthly_session_count = (user.monthly_session_count or 0) + 1
            db.session.commit()

    @staticmethod
    def increment_monthly_image_count(user_id):
        """Increment the user's monthly image counter after an image is generated."""
        user = User.query.get(user_id)
        if user:
            user.monthly_image_count = (user.monthly_image_count or 0) + 1
            db.session.commit()
