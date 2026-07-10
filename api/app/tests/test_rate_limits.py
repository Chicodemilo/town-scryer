# ==============================================================================
# File:      api/app/tests/test_rate_limits.py
# Purpose:   Unit tests for the rate limiter service. Covers monthly session
#            and image caps, monthly counter reset, session-level image cap,
#            and cost circuit breaker.
# Modified:  2026-06-01
# ==============================================================================
import pytest
from datetime import date, timedelta, datetime
from app.models.user import User
from app.models.session import Session
from app import db as _db
from app.services.rate_limiter_service import (
    RateLimiterService,
    MONTHLY_SESSION_CAP,
    MONTHLY_IMAGE_CAP,
    SESSION_IMAGE_CAP,
    SESSION_COST_LIMIT_CENTS,
)


def _create_user(db_session, **overrides):
    """Insert a User row with sensible defaults, applying any overrides."""
    defaults = dict(
        username='limuser',
        email='lim@example.com',
        password_hash='fakehash',
        monthly_image_count=0,
        monthly_session_count=0,
        monthly_image_reset_date=date.today() + timedelta(days=30),
    )
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    return user


def _create_session(db_session, user_id, **overrides):
    """Insert a Session row for the given user, applying any overrides."""
    defaults = dict(
        user_id=user_id,
        status='active',
        image_count=0,
        estimated_cost_cents=0,
        started_at=datetime.utcnow(),
    )
    defaults.update(overrides)
    session = Session(**defaults)
    db_session.add(session)
    db_session.commit()
    return session


class TestMonthlyLimits:
    """Monthly session and image cap enforcement."""

    def test_monthly_session_cap_blocks_start(self, app, db):
        """1. User at monthly session cap is blocked from starting (429)."""
        user = _create_user(_db.session, monthly_session_count=MONTHLY_SESSION_CAP)
        error, status = RateLimiterService.check_session_start_limits(user.id)
        assert status == 429
        assert 'session limit' in error.lower()

    def test_monthly_image_cap_blocks_start(self, app, db):
        """2. User at monthly image cap is blocked from starting (429)."""
        user = _create_user(_db.session, monthly_image_count=MONTHLY_IMAGE_CAP)
        error, status = RateLimiterService.check_session_start_limits(user.id)
        assert status == 429
        assert 'image limit' in error.lower()

    def test_monthly_reset_clears_counters(self, app, db):
        """3. User whose reset date is in the past gets counters zeroed."""
        user = _create_user(
            _db.session,
            monthly_session_count=10,
            monthly_image_count=100,
            monthly_image_reset_date=date.today() - timedelta(days=1),
        )
        error, status = RateLimiterService.check_session_start_limits(user.id)
        # Should pass now that counters are reset
        assert error is None
        assert status is None

        refreshed = User.query.get(user.id)
        assert refreshed.monthly_session_count == 0
        assert refreshed.monthly_image_count == 0
        assert refreshed.monthly_image_reset_date > date.today()


class TestChunkLevelLimits:
    """Session-level image cap and cost circuit breaker."""

    def test_session_image_cap_force_pauses(self, app, db):
        """4. Session at image cap returns force_paused."""
        user = _create_user(_db.session)
        session = _create_session(
            _db.session, user.id, image_count=SESSION_IMAGE_CAP
        )

        result = RateLimiterService.check_session_image_cap(session)
        assert result is not None
        assert result['force_paused'] is True
        assert result['reason'] == 'session_image_limit'

    def test_cost_circuit_breaker_force_pauses(self, app, db):
        """5. Session at cost limit returns force_paused."""
        user = _create_user(_db.session)
        session = _create_session(
            _db.session, user.id,
            estimated_cost_cents=SESSION_COST_LIMIT_CENTS,
        )

        result = RateLimiterService.check_cost_limit(session)
        assert result is not None
        assert result['force_paused'] is True
        assert result['reason'] == 'cost_limit'
