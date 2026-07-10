# ==============================================================================
# File:      api/app/routes/uploads.py
# Purpose:   Uploads route blueprint. Handles avatar file uploads with image
#            processing, and serves uploaded files.
# Callers:   routes/__init__.py
# Callees:   models/user.py, utils/uploads.py, security/__init__.py, Flask, db
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, request, jsonify, g, send_from_directory
from app import db
from app.models.user import User
from app.security import moderate_rate_limit, token_required
from app.utils.uploads import save_avatar, delete_avatar, UPLOAD_DIR
import os

uploads_bp = Blueprint('uploads', __name__)


@uploads_bp.route('/avatar', methods=['POST'])
@moderate_rate_limit
@token_required
def upload_avatar():
    """Upload or replace user avatar."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    base_name, error = save_avatar(file)
    if error:
        return jsonify({'error': error}), 400

    user = User.query.get(g.current_user['user_id'])
    if user.avatar:
        delete_avatar(user.avatar)
    user.avatar = base_name
    db.session.commit()
    return jsonify({'user': user.to_dict()}), 200


@uploads_bp.route('/<path:filepath>', methods=['GET'])
def serve_upload(filepath):
    """Serve uploaded files."""
    return send_from_directory(UPLOAD_DIR, filepath)
