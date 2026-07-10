# ==============================================================================
# File:      api/app/routes/characters.py
# Purpose:   Character route blueprint. Handles CRUD for player characters
#            linked to a game table, including portrait uploads.
# Callers:   routes/__init__.py
# Callees:   models/player_character.py, models/game_table.py,
#            models/table_member.py, utils/uploads.py, security/__init__.py,
#            Flask, db
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, jsonify, request, g
from app import db
from app.models.player_character import PlayerCharacter
from app.models.game_table import GameTable
from app.models.table_member import TableMember
from app.security import token_required
from app.utils.uploads import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from PIL import Image
import os
import uuid
import logging

characters_bp = Blueprint('characters', __name__)
logger = logging.getLogger(__name__)

PORTRAIT_SIZE = (512, 512)


def _ensure_portrait_dir():
    path = os.path.join(UPLOAD_DIR, 'portraits')
    os.makedirs(path, exist_ok=True)
    return path


def _is_table_member(table_id, user_id):
    return TableMember.query.filter_by(
        table_id=table_id, user_id=user_id
    ).first()


def _is_table_owner(table, user_id):
    return table is not None and table.owner_user_id == user_id


@characters_bp.route('/<int:table_id>/characters', methods=['POST'])
@token_required
def create_character(table_id):
    """Create a character on this table.

    Behavior:
      - Table owner (DM) may pass `unclaimed: true` to create a character with
        no `user_id`. The character can stay unclaimed forever; claiming is
        optional. Useful when the DM types in every player's character at
        session zero.
      - Anyone else (or a DM who omits `unclaimed`) self-claims the new
        character. The one-char-per-user-per-table rule still applies to
        claimed characters.
    """
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404

    if not _is_table_member(table_id, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json() or {}
    if not data.get('name'):
        return jsonify({'error': 'name is required'}), 400

    name = data['name'].strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'name must be 1-100 characters'}), 400

    unclaimed = bool(data.get('unclaimed')) and _is_table_owner(table, user_id)
    assign_user_id = None if unclaimed else user_id

    if assign_user_id is not None:
        existing = PlayerCharacter.query.filter_by(
            user_id=assign_user_id, table_id=table_id
        ).first()
        if existing:
            return jsonify({'error': 'You already have a character at this table'}), 409

    character = PlayerCharacter(
        user_id=assign_user_id,
        table_id=table_id,
        name=name,
        description=(data.get('description') or '').strip() or None,
    )
    db.session.add(character)
    db.session.commit()

    return jsonify(character.to_dict()), 201


@characters_bp.route('/<int:table_id>/characters/<int:char_id>', methods=['PUT'])
@token_required
def update_character(table_id, char_id):
    """Update a character.

    The character's claimer can edit it. The table owner (DM) can edit any
    character on their table, including unclaimed ones — important so that
    players who never claim still get their character maintained.
    """
    user_id = g.current_user.get('user_id')

    character = PlayerCharacter.query.filter_by(
        id=char_id, table_id=table_id
    ).first()
    if not character:
        return jsonify({'error': 'Character not found'}), 404

    table = GameTable.query.get(table_id)
    if character.user_id != user_id and not _is_table_owner(table, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'name' in data:
        name = data['name'].strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'name must be 1-100 characters'}), 400
        character.name = name

    if 'description' in data:
        character.description = data['description'].strip() or None

    db.session.commit()
    return jsonify(character.to_dict()), 200


@characters_bp.route('/<int:table_id>/characters', methods=['GET'])
@token_required
def list_characters(table_id):
    """List all characters for this table. Any member can view."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404

    if not _is_table_member(table_id, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    characters = PlayerCharacter.query.filter_by(table_id=table_id).all()
    return jsonify({
        'characters': [c.to_dict() for c in characters]
    }), 200


@characters_bp.route('/<int:table_id>/characters/<int:char_id>', methods=['DELETE'])
@token_required
def delete_character(table_id, char_id):
    """Delete a character. Character owner or table owner can delete."""
    user_id = g.current_user.get('user_id')

    character = PlayerCharacter.query.filter_by(
        id=char_id, table_id=table_id
    ).first()
    if not character:
        return jsonify({'error': 'Character not found'}), 404

    table = GameTable.query.get(table_id)
    if character.user_id != user_id and table.owner_user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    db.session.delete(character)
    db.session.commit()
    return jsonify({'message': 'Character deleted'}), 200


@characters_bp.route('/<int:table_id>/characters/<int:char_id>/portrait', methods=['POST'])
@token_required
def upload_portrait(table_id, char_id):
    """Upload portrait image. Character claimer or table owner (DM) can upload."""
    user_id = g.current_user.get('user_id')

    character = PlayerCharacter.query.filter_by(
        id=char_id, table_id=table_id
    ).first()
    if not character:
        return jsonify({'error': 'Character not found'}), 404

    table = GameTable.query.get(table_id)
    if character.user_id != user_id and not _is_table_owner(table, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    if 'portrait' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['portrait']
    if not file or not file.filename:
        return jsonify({'error': 'No file provided'}), 400

    # Validate extension
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({'error': 'Only JPG and PNG files are allowed'}), 400

    # Validate size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 5MB'}), 400

    try:
        portrait_dir = _ensure_portrait_dir()
        img = Image.open(file)
        img.thumbnail(PORTRAIT_SIZE, Image.LANCZOS)
        img = img.convert('RGB')

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(portrait_dir, filename)
        img.save(filepath, 'JPEG', quality=85)

        # Delete old portrait if exists
        if character.portrait_path:
            old_path = os.path.join(UPLOAD_DIR, character.portrait_path)
            if os.path.exists(old_path):
                os.remove(old_path)

        character.portrait_path = f"portraits/{filename}"
        db.session.commit()

        return jsonify(character.to_dict()), 200
    except Exception as e:
        logger.error(f"Portrait upload failed: {e}")
        return jsonify({'error': 'Failed to process image'}), 500


@characters_bp.route('/<int:table_id>/characters/<int:char_id>/claim', methods=['POST'])
@token_required
def claim_character(table_id, char_id):
    """Claim an unclaimed character. Caller must be a table member and not
    already have a claimed character on this table."""
    user_id = g.current_user.get('user_id')

    if not _is_table_member(table_id, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    character = PlayerCharacter.query.filter_by(
        id=char_id, table_id=table_id
    ).first()
    if not character:
        return jsonify({'error': 'Character not found'}), 404
    if character.user_id is not None:
        return jsonify({'error': 'Character already claimed'}), 409

    existing = PlayerCharacter.query.filter_by(
        user_id=user_id, table_id=table_id
    ).first()
    if existing:
        return jsonify({'error': 'You already have a character at this table'}), 409

    character.user_id = user_id
    db.session.commit()
    return jsonify(character.to_dict()), 200


@characters_bp.route('/characters/mine', methods=['GET'])
@token_required
def my_characters():
    """Return every character claimed by the current user, with the table name
    attached for display on the dashboard."""
    user_id = g.current_user.get('user_id')

    characters = PlayerCharacter.query.filter_by(user_id=user_id).all()
    results = []
    for c in characters:
        d = c.to_dict()
        table = GameTable.query.get(c.table_id) if c.table_id else None
        d['table_name'] = table.name if table else None
        results.append(d)
    return jsonify({'characters': results}), 200


@characters_bp.route('/<int:table_id>/characters/<int:char_id>/unclaim', methods=['POST'])
@token_required
def unclaim_character(table_id, char_id):
    """Release a claimed character back to unclaimed state. DM only — used to
    undo an accidental claim so the correct player can claim it instead."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not _is_table_owner(table, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    character = PlayerCharacter.query.filter_by(
        id=char_id, table_id=table_id
    ).first()
    if not character:
        return jsonify({'error': 'Character not found'}), 404
    if character.user_id is None:
        return jsonify({'error': 'Character is already unclaimed'}), 409

    character.user_id = None
    db.session.commit()
    return jsonify(character.to_dict()), 200
