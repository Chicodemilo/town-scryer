# ==============================================================================
# File:      api/app/routes/tables.py
# Purpose:   Table route blueprint. Handles CRUD for game tables, invite codes,
#            and table membership (join/leave).
# Callers:   routes/__init__.py
# Callees:   models/game_table.py, models/table_member.py, models/user.py,
#            security/__init__.py, Flask, db
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, jsonify, request, g
from app import db
from app.models.game_table import GameTable, _generate_invite_code
from app.models.table_member import TableMember
from app.models.player_character import PlayerCharacter
from app.models.user import User
from app.security import token_required
import logging

tables_bp = Blueprint('tables', __name__)
logger = logging.getLogger(__name__)


@tables_bp.route('', methods=['POST'])
@token_required
def create_table():
    """Create a new game table. Current user becomes owner."""
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    name = data['name'].strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'name must be 1-100 characters'}), 400

    # Generate unique invite code (retry on collision)
    for _ in range(10):
        code = _generate_invite_code()
        if not GameTable.query.filter_by(invite_code=code).first():
            break
    else:
        return jsonify({'error': 'Failed to generate invite code'}), 500

    table = GameTable(
        owner_user_id=user_id,
        name=name,
        invite_code=code,
    )
    db.session.add(table)
    db.session.flush()  # get table.id

    # Add owner as a member
    member = TableMember(
        table_id=table.id,
        user_id=user_id,
        role='owner',
    )
    db.session.add(member)
    db.session.commit()

    return jsonify({
        'id': table.id,
        'name': table.name,
        'invite_code': table.invite_code,
        'role': 'owner',
        'created_at': table.created_at.isoformat() if table.created_at else None,
    }), 201


@tables_bp.route('', methods=['GET'])
@token_required
def list_tables():
    """List all tables the current user is a member of."""
    user_id = g.current_user.get('user_id')

    memberships = (
        TableMember.query
        .filter_by(user_id=user_id)
        .all()
    )

    from app.models.session import Session

    results = []
    for m in memberships:
        table = GameTable.query.get(m.table_id)
        if not table:
            continue
        owner = User.query.get(table.owner_user_id)
        member_count = TableMember.query.filter_by(table_id=table.id).count()
        session_count = Session.query.filter_by(table_id=table.id).count()
        results.append({
            'id': table.id,
            'name': table.name,
            'invite_code': table.invite_code,
            'role': m.role,
            'member_count': member_count,
            'session_count': session_count,
            'owner_username': owner.username if owner else None,
            'created_at': table.created_at.isoformat() if table.created_at else None,
            # Per-table session defaults — needed so the Session setup form
            # can pre-fill when the DM picks this table.
            'game_type': table.game_type,
            'art_style': table.art_style,
            'rating': table.rating,
            'show_captions': bool(table.show_captions) if table.show_captions is not None else True,
            'show_daub_updates': bool(table.show_daub_updates) if table.show_daub_updates is not None else True,
            'scryer_name': table.scryer_name or 'Daub',
        })

    return jsonify({'tables': results}), 200


@tables_bp.route('/<int:table_id>', methods=['GET'])
@token_required
def get_table(table_id):
    """Get table detail. Must be a member."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404

    membership = TableMember.query.filter_by(
        table_id=table_id, user_id=user_id
    ).first()
    if not membership:
        return jsonify({'error': 'Forbidden'}), 403

    # Build members list
    members = []
    for m in TableMember.query.filter_by(table_id=table_id).all():
        user = User.query.get(m.user_id)
        character = PlayerCharacter.query.filter_by(
            user_id=m.user_id, table_id=table_id
        ).first()
        members.append({
            'user_id': m.user_id,
            'username': user.username if user else None,
            'character_name': character.name if character else None,
            'role': m.role,
            'joined_at': m.joined_at.isoformat() if m.joined_at else None,
        })

    result = {
        'id': table.id,
        'name': table.name,
        'owner_user_id': table.owner_user_id,
        'members': members,
        'created_at': table.created_at.isoformat() if table.created_at else None,
    }

    # Only show invite_code to owner
    if membership.role == 'owner':
        result['invite_code'] = table.invite_code

    return jsonify(result), 200


@tables_bp.route('/join', methods=['POST'])
@token_required
def join_table():
    """Join a table by invite code."""
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('invite_code'):
        return jsonify({'error': 'invite_code is required'}), 400

    code = data['invite_code'].strip().upper()
    table = GameTable.query.filter_by(invite_code=code).first()
    if not table:
        return jsonify({'error': 'Invalid invite code'}), 404

    # Check if already a member
    existing = TableMember.query.filter_by(
        table_id=table.id, user_id=user_id
    ).first()
    if existing:
        return jsonify({'error': 'Already a member of this table'}), 409

    member = TableMember(
        table_id=table.id,
        user_id=user_id,
        role='player',
    )
    db.session.add(member)
    db.session.commit()

    return jsonify({
        'id': table.id,
        'name': table.name,
        'role': 'player',
    }), 200


@tables_bp.route('/<int:table_id>/regenerate-code', methods=['POST'])
@token_required
def regenerate_code(table_id):
    """Regenerate invite code. Owner only."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404
    if table.owner_user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    # Generate new unique code
    for _ in range(10):
        code = _generate_invite_code()
        if not GameTable.query.filter_by(invite_code=code).first():
            break
    else:
        return jsonify({'error': 'Failed to generate invite code'}), 500

    table.invite_code = code
    db.session.commit()

    return jsonify({'invite_code': table.invite_code}), 200


@tables_bp.route('/<int:table_id>', methods=['PUT'])
@token_required
def update_table(table_id):
    """Update mutable table fields. DM only. Supports notes, show_captions,
    and the per-table session defaults (game_type/art_style/rating)."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404
    if table.owner_user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json() or {}
    if 'show_captions' in data:
        table.show_captions = bool(data.get('show_captions'))
    if 'show_daub_updates' in data:
        table.show_daub_updates = bool(data.get('show_daub_updates'))
    if 'game_type' in data:
        table.game_type = (data.get('game_type') or '').strip() or None
    if 'art_style' in data:
        table.art_style = (data.get('art_style') or '').strip() or None
    if 'rating' in data:
        table.rating = (data.get('rating') or '').strip() or None
    if 'scene_model' in data:
        # Empty string / None means "use system default" — store as NULL.
        sm = (data.get('scene_model') or '').strip()
        table.scene_model = sm or None
    if 'notes' in data:
        # Empty string clears notes; otherwise trim and store.
        notes = data.get('notes')
        table.notes = (notes or '').strip() or None

    db.session.commit()
    return jsonify(table.to_dict()), 200


@tables_bp.route('/<int:table_id>', methods=['DELETE'])
@token_required
def delete_table(table_id):
    """Delete a table. Owner only."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404
    if table.owner_user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    db.session.delete(table)
    db.session.commit()

    return jsonify({'message': 'Table deleted'}), 200


@tables_bp.route('/<int:table_id>/leave', methods=['DELETE'])
@token_required
def leave_table(table_id):
    """Leave a table. Removes membership and character. Owner cannot leave."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404

    if table.owner_user_id == user_id:
        return jsonify({'error': 'Owner cannot leave. Delete the table instead.'}), 400

    membership = TableMember.query.filter_by(
        table_id=table_id, user_id=user_id
    ).first()
    if not membership:
        return jsonify({'error': 'Not a member of this table'}), 404

    # Remove player's character for this table
    character = PlayerCharacter.query.filter_by(
        user_id=user_id, table_id=table_id
    ).first()
    if character:
        db.session.delete(character)

    db.session.delete(membership)
    db.session.commit()

    return jsonify({'message': 'Left table successfully'}), 200
