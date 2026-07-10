# ==============================================================================
# File:      api/app/security/__init__.py
# Purpose:   Package init for security middleware. Re-exports rate limiting,
#            JWT auth, and security header utilities for convenient
#            importing across the application.
# Callers:   app/__init__.py, routes/admin.py, routes/auth.py,
#            routes/uploads.py, security/examples.py
# Callees:   security/rate_limiter.py, security/auth_middleware.py,
#            security/security_headers.py
# Modified:  2026-04-22
# ==============================================================================
"""
Security Middleware Package for Flask API

This package provides comprehensive security middleware including:
- Rate limiting with sliding window algorithm
- JWT authentication and authorization
- Security headers and CORS protection
- Input validation and sanitization utilities

Usage:
    from app.security import rate_limiter, auth_middleware, security_headers
    from app.security.rate_limiter import rate_limit, strict_rate_limit
    from app.security.auth_middleware import token_required, admin_required
"""

from .rate_limiter import (
    rate_limiter,
    rate_limit,
    strict_rate_limit,
    moderate_rate_limit,
    lenient_rate_limit,
    admin_rate_limit,
    get_rate_limit_status,
    cleanup_rate_limiter
)

from .auth_middleware import (
    auth_middleware,
    token_required,
    admin_required,
    optional_auth,
    role_required,
    validate_api_key,
    permission_required,
    get_user_permissions,
    has_permission,
    create_refresh_token,
    refresh_access_token
)

from .security_headers import (
    security_headers,
    generate_csp_nonce,
    get_csp_nonce,
    is_safe_url,
    hash_password,
    verify_password,
    sanitize_filename,
    validate_input_length,
    escape_html,
    sanitize_text
)

__all__ = [
    # Rate Limiting
    'rate_limiter',
    'rate_limit',
    'strict_rate_limit',
    'moderate_rate_limit',
    'lenient_rate_limit',
    'admin_rate_limit',
    'get_rate_limit_status',
    'cleanup_rate_limiter',
    
    # Authentication & Authorization
    'auth_middleware',
    'token_required',
    'admin_required',
    'optional_auth',
    'role_required',
    'validate_api_key',
    'permission_required',
    'get_user_permissions',
    'has_permission',
    'create_refresh_token',
    'refresh_access_token',
    
    # Security Headers & Utilities
    'security_headers',
    'generate_csp_nonce',
    'get_csp_nonce',
    'is_safe_url',
    'hash_password',
    'verify_password',
    'sanitize_filename',
    'validate_input_length',
    'escape_html',
    'sanitize_text'
]
