# ==============================================================================
# File:      api/app/routes/history.py
# Purpose:   Session history route blueprint. Provides paginated lists of past
#            sessions and their scenes for the authenticated user.
# Callers:   routes/__init__.py
# Callees:   models/session.py, models/scene.py, security/__init__.py, Flask
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, jsonify, request, g
from app.models.session import Session
from app.models.scene import Scene
from app.models.game_table import GameTable
from app.security import token_required
from app import db
import logging

history_bp = Blueprint('history', __name__)
logger = logging.getLogger('security')


@history_bp.route('', methods=['GET'])
@token_required
def list_sessions():
    """List the authenticated user's past sessions, newest first.
    Supports ?page=1&per_page=20 pagination."""
    user_id = g.current_user.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)  # cap page size

    pagination = (
        Session.query
        .filter_by(user_id=user_id)
        .order_by(Session.started_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    sessions = []
    for s in pagination.items:
        duration_seconds = None
        if s.started_at and s.ended_at:
            duration_seconds = int(
                (s.ended_at - s.started_at).total_seconds()
            )
        elif s.started_at:
            from datetime import datetime
            duration_seconds = int(
                (datetime.utcnow() - s.started_at).total_seconds()
            )

        table_name = None
        if s.table_id:
            table = GameTable.query.get(s.table_id)
            table_name = table.name if table else None

        # Append 'Z' so the browser parses these as UTC, not local time.
        sessions.append({
            'id': s.id,
            'started_at': (s.started_at.isoformat() + 'Z') if s.started_at else None,
            'ended_at': (s.ended_at.isoformat() + 'Z') if s.ended_at else None,
            'status': s.status,
            'image_count': s.image_count,
            'duration_seconds': duration_seconds,
            'game_type': s.game_type,
            'art_style': s.art_style,
            'rating': s.rating,
            'table_name': table_name,
        })

    return jsonify({
        'sessions': sessions,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    }), 200


@history_bp.route('/<int:session_id>/scenes', methods=['GET'])
@token_required
def list_session_scenes(session_id):
    """List all scenes for a session. 403 if session doesn't belong to the user.
    Supports ?page=1&per_page=20 pagination."""
    user_id = g.current_user.get('user_id')

    session = Session.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if session.user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    pagination = (
        Scene.query
        .filter_by(session_id=session_id)
        .order_by(Scene.created_at.asc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    scenes = []
    for sc in pagination.items:
        scenes.append({
            'id': sc.id,
            'image_url': sc.image_url,
            'image_path': sc.image_path,
            'scene_description': sc.scene_description,
            'caption': sc.caption,
            'prompt': sc.prompt,
            'created_at': (sc.created_at.isoformat() + 'Z') if sc.created_at else None,
        })

    return jsonify({
        'scenes': scenes,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages,
    }), 200


@history_bp.route('/<int:session_id>', methods=['DELETE'])
@token_required
def delete_session(session_id):
    """Delete a session and all its scenes. Must belong to the caller."""
    user_id = g.current_user.get('user_id')

    session = Session.query.get(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if session.user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    # Scene cascade-delete is configured on the Session.scenes relationship.
    db.session.delete(session)
    db.session.commit()
    return jsonify({'deleted': True, 'session_id': session_id}), 200
