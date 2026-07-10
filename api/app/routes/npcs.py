# ==============================================================================
# File:      api/app/routes/npcs.py
# Purpose:   NPC route blueprint. CRUD for recurring non-player characters
#            scoped to a game table. Only the table owner (DM) can manage
#            NPCs; members can read.
# Callers:   routes/__init__.py
# Callees:   models/npc.py, models/game_table.py, models/table_member.py,
#            security/__init__.py, Flask, db
# Modified:  2026-06-05
# ==============================================================================
from flask import Blueprint, jsonify, request, g
from app import db
from app.models.npc import Npc
from app.models.game_table import GameTable
from app.models.table_member import TableMember
from app.security import token_required
import logging

npcs_bp = Blueprint('npcs', __name__)
logger = logging.getLogger(__name__)


def _is_table_member(table_id, user_id):
    return TableMember.query.filter_by(
        table_id=table_id, user_id=user_id
    ).first()


def _is_table_owner(table, user_id):
    return table is not None and table.owner_user_id == user_id


@npcs_bp.route('/<int:table_id>/npcs', methods=['GET'])
@token_required
def list_npcs(table_id):
    """List all NPCs for this table. Any member can view."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404
    if not _is_table_member(table_id, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    npcs = Npc.query.filter_by(table_id=table_id).all()
    return jsonify({'npcs': [n.to_dict() for n in npcs]}), 200


@npcs_bp.route('/<int:table_id>/npcs', methods=['POST'])
@token_required
def create_npc(table_id):
    """Create an NPC on this table. DM only."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not table:
        return jsonify({'error': 'Table not found'}), 404
    if not _is_table_owner(table, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'name must be 1-100 characters'}), 400

    npc = Npc(
        table_id=table_id,
        name=name,
        description=(data.get('description') or '').strip() or None,
    )
    db.session.add(npc)
    db.session.commit()
    return jsonify(npc.to_dict()), 201


@npcs_bp.route('/<int:table_id>/npcs/<int:npc_id>', methods=['PUT'])
@token_required
def update_npc(table_id, npc_id):
    """Update an NPC. DM only."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not _is_table_owner(table, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    npc = Npc.query.filter_by(id=npc_id, table_id=table_id).first()
    if not npc:
        return jsonify({'error': 'NPC not found'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name or len(name) > 100:
            return jsonify({'error': 'name must be 1-100 characters'}), 400
        npc.name = name
    if 'description' in data:
        npc.description = (data.get('description') or '').strip() or None

    db.session.commit()
    return jsonify(npc.to_dict()), 200


@npcs_bp.route('/<int:table_id>/npcs/<int:npc_id>', methods=['DELETE'])
@token_required
def delete_npc(table_id, npc_id):
    """Delete an NPC. DM only."""
    user_id = g.current_user.get('user_id')

    table = GameTable.query.get(table_id)
    if not _is_table_owner(table, user_id):
        return jsonify({'error': 'Forbidden'}), 403

    npc = Npc.query.filter_by(id=npc_id, table_id=table_id).first()
    if not npc:
        return jsonify({'error': 'NPC not found'}), 404

    db.session.delete(npc)
    db.session.commit()
    return jsonify({'message': 'NPC deleted'}), 200
