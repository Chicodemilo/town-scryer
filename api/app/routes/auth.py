# ==============================================================================
# File:      api/app/routes/auth.py
# Purpose:   Auth route blueprint. Handles user registration, login, token
#            verification, profile, email verification/change, terms
#            acceptance, and invite completion.
# Callers:   routes/__init__.py
# Callees:   services/auth_service.py, security/__init__.py, Flask
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, jsonify, request, g
from app.services.auth_service import AuthService
from app.security import auth_middleware, moderate_rate_limit, token_required
import logging

auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger('security')


@auth_bp.route('/register', methods=['POST'])
@moderate_rate_limit
def register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return jsonify({'error': 'Username, email, and password required'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    user, error = AuthService.register(username, email, password)
    if error:
        return jsonify({'error': error}), 409

    token = auth_middleware.generate_token(user.to_dict())
    logger.info(f"New user registered: {username}")

    return jsonify({
        'token': token,
        'user': user.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
@moderate_rate_limit
def login():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        logger.warning(f"Invalid login attempt from {request.remote_addr}")
        return jsonify({'error': 'Username and password required'}), 400

    user = AuthService.authenticate(data['username'], data['password'])
    if not user:
        logger.warning(f"Failed login attempt for user: {data.get('username')} from {request.remote_addr}")
        return jsonify({'error': 'Invalid credentials'}), 401

    token = auth_middleware.generate_token(user.to_dict())

    return jsonify({
        'success': True,
        'token': token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/verify', methods=['GET'])
@token_required
def verify_token():
    return jsonify({
        'valid': True,
        'user': {
            'id': g.current_user.get('user_id'),
            'username': g.current_user.get('username'),
            'roles': g.current_user.get('roles', [])
        }
    }), 200


@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    user = AuthService.get_user_by_id(g.current_user.get('user_id'))
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/verify-email', methods=['GET'])
@moderate_rate_limit
def verify_email():
    token = request.args.get('token')
    user, error = AuthService.verify_email(token)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Email verified successfully', 'user': user.to_dict()}), 200


@auth_bp.route('/resend-verification', methods=['POST'])
@token_required
def resend_verification():
    user_id = g.current_user.get('user_id')
    user, error = AuthService.resend_verification(user_id)
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'message': 'Verification email sent'}), 200


@auth_bp.route('/accept-terms', methods=['PUT'])
@token_required
def accept_terms():
    user, error = AuthService.accept_terms(g.current_user.get('user_id'))
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/terms', methods=['GET'])
def get_terms():
    terms = AuthService.get_terms()
    return jsonify({'terms': terms.to_dict()}), 200


@auth_bp.route('/change-email', methods=['PUT'])
@token_required
@moderate_rate_limit
def change_email():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'New email required'}), 400
    user, error = AuthService.change_email(g.current_user.get('user_id'), data['email'])
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'user': user.to_dict(), 'message': 'Verification email sent to new address'}), 200


@auth_bp.route('/verify-new-email', methods=['GET'])
@moderate_rate_limit
def verify_new_email():
    token = request.args.get('token')
    user, error = AuthService.verify_new_email(token)
    if error:
        return jsonify({'error': error}), 400
    new_token = auth_middleware.generate_token(user.to_dict())
    return jsonify({'message': 'Email updated successfully', 'user': user.to_dict(), 'token': new_token}), 200


@auth_bp.route('/complete-invite', methods=['POST'])
@moderate_rate_limit
def complete_invite():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body required'}), 400
    token = data.get('token')
    username = data.get('username')
    password = data.get('password')
    if not all([token, username, password]):
        return jsonify({'error': 'Token, username, and password required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    user, error = AuthService.complete_invite(token, username, password)
    if error:
        return jsonify({'error': error}), 400
    from app.security import auth_middleware as am
    jwt_token = am.generate_token(user.to_dict())
    return jsonify({'token': jwt_token, 'user': user.to_dict()}), 200
