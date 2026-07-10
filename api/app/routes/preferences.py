# ==============================================================================
# File:      api/app/routes/preferences.py
# Purpose:   Preferences route blueprint. Handles reading and updating per-user
#            default settings for game type, art style, and gore level.
# Callers:   routes/__init__.py
# Callees:   services/preferences_service.py, security/__init__.py, Flask
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, jsonify, request, g
from app.services.preferences_service import PreferencesService
from app.security import token_required
import logging

preferences_bp = Blueprint('preferences', __name__)
logger = logging.getLogger('security')


@preferences_bp.route('', methods=['GET'])
@token_required
def get_preferences():
    user_id = g.current_user.get('user_id')
    prefs = PreferencesService.get_preferences(user_id)
    return jsonify(prefs), 200


@preferences_bp.route('', methods=['POST'])
@token_required
def update_preferences():
    user_id = g.current_user.get('user_id')
    data = request.get_json(silent=True) or {}

    game_type = data.get('game_type')
    art_style = data.get('art_style')
    rating = data.get('rating')

    prefs = PreferencesService.upsert_preferences(
        user_id,
        game_type=game_type,
        art_style=art_style,
        rating=rating,
    )
    return jsonify(prefs), 200
