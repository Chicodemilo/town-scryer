# ==============================================================================
# File:      api/app/security/auth_middleware.py
# Purpose:   JWT authentication and authorization middleware. Provides token
#            generation/verification, decorators for protected endpoints
#            (token_required, admin_required, role_required), API key
#            validation, and permission utilities.
# Callers:   security/__init__.py, app/__init__.py, routes/auth.py,
#            routes/admin.py
# Callees:   jwt (PyJWT), Flask, werkzeug.security, os, functools, datetime
# Modified:  2026-04-22
# ==============================================================================
"""
Authentication and Authorization Middleware for Flask API

Provides JWT token validation, user authentication, and role-based access control.
Integrates with the existing user model and admin system.
"""

import jwt
import functools
from datetime import datetime, timedelta
from flask import request, jsonify, g, current_app
from werkzeug.security import check_password_hash
import os

class AuthMiddleware:
    """
    Authentication middleware for handling JWT tokens and user sessions
    """
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the auth middleware with Flask app"""
        app.config.setdefault('JWT_SECRET_KEY', os.environ.get('JWT_SECRET_KEY', 'dev-secret-key-change-in-production'))
        app.config.setdefault('JWT_EXPIRATION_HOURS', 24)
        app.config.setdefault('JWT_ALGORITHM', 'HS256')
        
        # Store reference to app
        self.app = app
    
    def generate_token(self, user_data, expires_in_hours=None):
        """
        Generate JWT token for user
        
        Args:
            user_data (dict): User information to encode in token
            expires_in_hours (int): Token expiration time (optional)
            
        Returns:
            str: JWT token
        """
        if expires_in_hours is None:
            expires_in_hours = current_app.config['JWT_EXPIRATION_HOURS']
        
        payload = {
            'user_id': user_data.get('id'),
            'email': user_data.get('email'),
            'username': user_data.get('username'),
            'is_admin': user_data.get('is_admin', False),
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        return jwt.encode(
            payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm=current_app.config['JWT_ALGORITHM']
        )
    
    def verify_token(self, token):
        """
        Verify and decode JWT token
        
        Args:
            token (str): JWT token to verify
            
        Returns:
            dict: Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=[current_app.config['JWT_ALGORITHM']]
            )
            
            # Check token type
            if payload.get('type') != 'access':
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def get_current_user(self):
        """
        Get current user from request context
        
        Returns:
            dict: Current user data or None
        """
        return getattr(g, 'current_user', None)
    
    def extract_token_from_request(self):
        """
        Extract JWT token from request headers
        
        Returns:
            str: JWT token or None
        """
        # Check Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        
        # Check X-Access-Token header
        return request.headers.get('X-Access-Token')

# Global auth middleware instance
auth_middleware = AuthMiddleware()

def token_required(f):
    """
    Decorator to require valid JWT token
    Sets g.current_user with decoded token data
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = auth_middleware.extract_token_from_request()
        
        if not token:
            return jsonify({
                'error': 'Authentication required',
                'message': 'No token provided'
            }), 401
        
        payload = auth_middleware.verify_token(token)
        
        if not payload:
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Invalid or expired token'
            }), 401

        # Verify user is still active
        from app.models.user import User
        user = User.query.get(payload.get('user_id'))
        if not user or not user.is_active:
            return jsonify({
                'error': 'Authentication failed',
                'message': 'Account is deactivated or does not exist'
            }), 401

        # Set current user in request context
        g.current_user = payload

        return f(*args, **kwargs)

    return decorated

def admin_required(f):
    """
    Decorator to require admin privileges
    Must be used with @token_required
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({
                'error': 'Authentication required',
                'message': 'No user context found'
            }), 401
        
        if not g.current_user.get('is_admin', False):
            return jsonify({
                'error': 'Authorization failed',
                'message': 'Admin privileges required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated

def optional_auth(f):
    """
    Decorator for optional authentication
    Sets g.current_user if valid token is provided, but doesn't require it
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        token = auth_middleware.extract_token_from_request()
        
        if token:
            payload = auth_middleware.verify_token(token)
            if payload:
                g.current_user = payload
        
        # Always continue, whether authenticated or not
        return f(*args, **kwargs)
    
    return decorated

def role_required(*required_roles):
    """
    Decorator to require specific roles
    Must be used with @token_required
    
    Args:
        *required_roles: List of required roles
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'No user context found'
                }), 401
            
            user_roles = g.current_user.get('roles', [])
            
            # Admin users have all roles
            if g.current_user.get('is_admin', False):
                return f(*args, **kwargs)
            
            # Check if user has any of the required roles
            if not any(role in user_roles for role in required_roles):
                return jsonify({
                    'error': 'Authorization failed',
                    'message': f'One of these roles required: {", ".join(required_roles)}'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator

def validate_api_key(f):
    """
    Decorator to validate API key from headers
    Alternative to JWT for service-to-service communication
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'X-API-Key header is required'
            }), 401
        
        # Get valid API keys from environment or config
        valid_api_keys = current_app.config.get('VALID_API_KEYS', [])
        env_api_key = os.environ.get('API_KEY')
        if env_api_key:
            valid_api_keys.append(env_api_key)
        
        if api_key not in valid_api_keys:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is not valid'
            }), 401
        
        # Set API key context
        g.api_key = api_key
        
        return f(*args, **kwargs)
    
    return decorated

def get_user_permissions():
    """
    Get current user's permissions
    
    Returns:
        list: List of user permissions
    """
    if not hasattr(g, 'current_user') or not g.current_user:
        return []
    
    permissions = []
    
    # Admin users have all permissions
    if g.current_user.get('is_admin', False):
        permissions.extend([
            'read_users', 'write_users', 'delete_users',
            'read_content', 'write_content', 'delete_content',
            'read_admin', 'write_admin',
            'read_logs', 'write_logs'
        ])
    else:
        # Regular users have basic permissions
        permissions.extend([
            'read_content', 'write_content'
        ])
    
    return permissions

def has_permission(permission):
    """
    Check if current user has specific permission
    
    Args:
        permission (str): Permission to check
        
    Returns:
        bool: True if user has permission
    """
    return permission in get_user_permissions()

def permission_required(permission):
    """
    Decorator to require specific permission
    Must be used with @token_required
    
    Args:
        permission (str): Required permission
    """
    def decorator(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not has_permission(permission):
                return jsonify({
                    'error': 'Permission denied',
                    'message': f'Permission "{permission}" is required'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator

def create_refresh_token(user_data):
    """
    Create refresh token for user
    
    Args:
        user_data (dict): User information
        
    Returns:
        str: Refresh token
    """
    payload = {
        'user_id': user_data.get('id'),
        'exp': datetime.utcnow() + timedelta(days=30),  # 30 days
        'iat': datetime.utcnow(),
        'type': 'refresh'
    }
    
    return jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )

def refresh_access_token(refresh_token):
    """
    Generate new access token from refresh token
    
    Args:
        refresh_token (str): Valid refresh token
        
    Returns:
        str: New access token or None if invalid
    """
    try:
        payload = jwt.decode(
            refresh_token,
            current_app.config['JWT_SECRET_KEY'],
            algorithms=[current_app.config['JWT_ALGORITHM']]
        )
        
        if payload.get('type') != 'refresh':
            return None
        
        # Here you would typically fetch fresh user data from database
        # For now, we'll create a minimal user object
        user_data = {
            'id': payload.get('user_id'),
            'email': None,  # Would fetch from DB
            'username': None,  # Would fetch from DB
            'is_admin': False  # Would fetch from DB
        }
        
        return auth_middleware.generate_token(user_data)
        
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
