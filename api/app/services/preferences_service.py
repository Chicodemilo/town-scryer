# ==============================================================================
# File:      api/app/services/preferences_service.py
# Purpose:   Preferences management service. Handles reading and upserting
#            per-user default settings for game type, art style, and gore level.
# Callers:   routes/preferences.py
# Callees:   models/user_preferences.py, SQLAlchemy (db)
# Modified:  2026-06-01
# ==============================================================================
from app import db
from app.models.user_preferences import UserPreferences
import logging

logger = logging.getLogger(__name__)

DEFAULTS = {
    'game_type': 'fantasy_dnd',
    'art_style': 'frazetta',
    'rating': 'PG-13',
}


class PreferencesService:
    """Handles reading and upserting user preferences."""

    @staticmethod
    def get_preferences(user_id):
        """Return the user's preferences dict. Falls back to defaults."""
        prefs = UserPreferences.query.filter_by(user_id=user_id).first()
        if prefs:
            return prefs.to_dict()
        return {
            'user_id': user_id,
            'game_type': DEFAULTS['game_type'],
            'art_style': DEFAULTS['art_style'],
            'rating': DEFAULTS['rating'],
        }

    @staticmethod
    def upsert_preferences(user_id, game_type=None, art_style=None, rating=None):
        """Create or update preferences for the user. Returns the preferences dict."""
        prefs = UserPreferences.query.filter_by(user_id=user_id).first()
        if prefs:
            if game_type is not None:
                prefs.game_type = game_type
            if art_style is not None:
                prefs.art_style = art_style
            if rating is not None:
                prefs.rating = rating
        else:
            prefs = UserPreferences(
                user_id=user_id,
                game_type=game_type or DEFAULTS['game_type'],
                art_style=art_style or DEFAULTS['art_style'],
                rating=rating or DEFAULTS['rating'],
            )
            db.session.add(prefs)

        db.session.commit()
        logger.info(f"Preferences upserted for user {user_id}")
        return prefs.to_dict()
