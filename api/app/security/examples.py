# ==============================================================================
# File:      api/app/security/examples.py
# Purpose:   Reference examples demonstrating how to use all security
#            middleware components (rate limiting, auth, headers, CSP,
#            input validation). Not imported by the application itself.
# Callers:   (none -- documentation/reference only)
# Callees:   security/__init__.py, Flask
# Modified:  2026-04-22
# ==============================================================================
"""
Security Middleware Usage Examples for Flask API

This file contains comprehensive examples of how to use all the security
middleware components in your Flask application.
"""

from flask import Flask, request, jsonify, g
from app.security import (
    # Rate Limiting
    rate_limit, strict_rate_limit, moderate_rate_limit, lenient_rate_limit, admin_rate_limit,
    get_rate_limit_status, cleanup_rate_limiter,
    
    # Authentication & Authorization
    auth_middleware, token_required, admin_required, optional_auth, role_required,
    validate_api_key, permission_required, get_user_permissions, has_permission,
    create_refresh_token, refresh_access_token,
    
    # Security Headers & Utilities
    security_headers, generate_csp_nonce, get_csp_nonce, is_safe_url,
    hash_password, verify_password, sanitize_filename, validate_input_length, escape_html
)

# Initialize Flask app with security middleware
app = Flask(__name__)

# Initialize security middleware
auth_middleware.init_app(app)
security_headers.init_app(app)

# =============================================================================
# RATE LIMITING EXAMPLES
# =============================================================================

@app.route('/api/public')
@lenient_rate_limit  # 100 requests/minute, 2000/hour
def public_endpoint():
    """Public endpoint with lenient rate limiting"""
    return jsonify({'message': 'This is a public endpoint'})

@app.route('/api/data')
@moderate_rate_limit  # 30 requests/minute, 500/hour
def get_data():
    """Standard API endpoint with moderate rate limiting"""
    return jsonify({'data': ['item1', 'item2', 'item3']})

@app.route('/api/sensitive')
@strict_rate_limit  # 10 requests/minute, 100/hour
def sensitive_endpoint():
    """Sensitive endpoint with strict rate limiting"""
    return jsonify({'sensitive': 'information'})

@app.route('/api/admin/bulk-operation')
@admin_rate_limit  # 200 requests/minute, 5000/hour
def admin_bulk_operation():
    """Admin endpoint with higher rate limits"""
    return jsonify({'status': 'bulk operation completed'})

@app.route('/api/custom-rate-limit')
@rate_limit(requests_per_minute=5, requests_per_hour=50, per_user_multiplier=3)
def custom_rate_limit():
    """Custom rate limiting configuration"""
    return jsonify({'message': 'Custom rate limited endpoint'})

@app.route('/api/rate-limit-status')
def rate_limit_status():
    """Get current rate limit status for debugging"""
    status = get_rate_limit_status()
    return jsonify(status)

# =============================================================================
# AUTHENTICATION & AUTHORIZATION EXAMPLES
# =============================================================================

@app.route('/api/auth/login', methods=['POST'])
@moderate_rate_limit
def login():
    """User login endpoint"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    # Validate input
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Here you would validate credentials against database
    # For demo purposes, we'll use dummy data
    if email == 'user@example.com' and password == 'password123':
        user_data = {
            'id': 1,
            'email': email,
            'username': 'testuser',
            'is_admin': False
        }
        
        # Generate tokens
        access_token = auth_middleware.generate_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        return jsonify({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/auth/refresh', methods=['POST'])
@moderate_rate_limit
def refresh_token():
    """Refresh access token using refresh token"""
    data = request.get_json()
    refresh_token_str = data.get('refresh_token')
    
    if not refresh_token_str:
        return jsonify({'error': 'Refresh token required'}), 400
    
    new_access_token = refresh_access_token(refresh_token_str)
    
    if new_access_token:
        return jsonify({'access_token': new_access_token})
    
    return jsonify({'error': 'Invalid or expired refresh token'}), 401

@app.route('/api/protected')
@token_required
@moderate_rate_limit
def protected_endpoint():
    """Protected endpoint requiring valid JWT token"""
    user = g.current_user
    return jsonify({
        'message': 'This is a protected endpoint',
        'user_id': user.get('user_id'),
        'email': user.get('email')
    })

@app.route('/api/admin/users')
@token_required
@admin_required
@admin_rate_limit
def admin_users():
    """Admin-only endpoint"""
    return jsonify({
        'message': 'Admin access granted',
        'users': [
            {'id': 1, 'email': 'user1@example.com'},
            {'id': 2, 'email': 'user2@example.com'}
        ]
    })

@app.route('/api/optional-auth')
@optional_auth
@lenient_rate_limit
def optional_auth_endpoint():
    """Endpoint with optional authentication"""
    user = getattr(g, 'current_user', None)
    
    if user:
        return jsonify({
            'message': 'Authenticated user',
            'user_id': user.get('user_id')
        })
    else:
        return jsonify({
            'message': 'Anonymous user'
        })

@app.route('/api/role-based')
@token_required
@role_required('editor', 'moderator')
@moderate_rate_limit
def role_based_endpoint():
    """Endpoint requiring specific roles"""
    return jsonify({
        'message': 'Access granted based on role',
        'user_roles': g.current_user.get('roles', [])
    })

@app.route('/api/permission-based')
@token_required
@permission_required('write_content')
@moderate_rate_limit
def permission_based_endpoint():
    """Endpoint requiring specific permission"""
    return jsonify({
        'message': 'Access granted based on permission',
        'user_permissions': get_user_permissions()
    })

@app.route('/api/service-to-service')
@validate_api_key
@moderate_rate_limit
def service_endpoint():
    """Service-to-service endpoint using API key"""
    return jsonify({
        'message': 'Service authenticated',
        'api_key': g.api_key[:8] + '...'  # Show only first 8 chars
    })

# =============================================================================
# SECURITY UTILITIES EXAMPLES
# =============================================================================

@app.route('/api/upload', methods=['POST'])
@token_required
@moderate_rate_limit
def upload_file():
    """File upload with filename sanitization"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Sanitize filename for security
    safe_filename = sanitize_filename(file.filename)
    
    return jsonify({
        'message': 'File uploaded successfully',
        'original_filename': file.filename,
        'safe_filename': safe_filename
    })

@app.route('/api/user-input', methods=['POST'])
@token_required
@moderate_rate_limit
def process_user_input():
    """Process user input with validation and sanitization"""
    data = request.get_json()
    user_input = data.get('content', '')
    
    # Validate input length
    if not validate_input_length(user_input, max_length=500):
        return jsonify({'error': 'Input too long (max 500 characters)'}), 400
    
    # Escape HTML to prevent XSS
    safe_content = escape_html(user_input)
    
    return jsonify({
        'message': 'Input processed successfully',
        'original': user_input,
        'sanitized': safe_content
    })

@app.route('/api/redirect')
@token_required
@moderate_rate_limit
def safe_redirect():
    """Safe redirect with URL validation"""
    redirect_url = request.args.get('url', '/')
    
    if is_safe_url(redirect_url):
        return jsonify({
            'message': 'Redirect is safe',
            'redirect_url': redirect_url
        })
    else:
        return jsonify({
            'error': 'Unsafe redirect URL',
            'safe_url': '/'
        }), 400

@app.route('/api/password-hash', methods=['POST'])
@token_required
@admin_required
@strict_rate_limit
def hash_user_password():
    """Hash password securely (admin only)"""
    data = request.get_json()
    password = data.get('password')
    
    if not password:
        return jsonify({'error': 'Password required'}), 400
    
    hashed, salt = hash_password(password)
    
    return jsonify({
        'message': 'Password hashed successfully',
        'hash': hashed,
        'salt': salt
    })

@app.route('/api/password-verify', methods=['POST'])
@token_required
@admin_required
@strict_rate_limit
def verify_user_password():
    """Verify password against hash (admin only)"""
    data = request.get_json()
    password = data.get('password')
    stored_hash = data.get('hash')
    salt = data.get('salt')
    
    if not all([password, stored_hash, salt]):
        return jsonify({'error': 'Password, hash, and salt required'}), 400
    
    is_valid = verify_password(password, stored_hash, salt)
    
    return jsonify({
        'message': 'Password verification completed',
        'is_valid': is_valid
    })

# =============================================================================
# CSP AND SECURITY HEADERS EXAMPLES
# =============================================================================

@app.route('/api/secure-page')
@token_required
@moderate_rate_limit
def secure_page():
    """Endpoint demonstrating CSP nonce usage"""
    nonce = generate_csp_nonce()
    
    return jsonify({
        'message': 'Secure page with CSP nonce',
        'csp_nonce': nonce,
        'inline_script': f'<script nonce="{nonce}">console.log("Secure script");</script>'
    })

@app.route('/api/security-headers-demo')
@lenient_rate_limit
def security_headers_demo():
    """Endpoint to demonstrate security headers"""
    return jsonify({
        'message': 'Check response headers for security configuration',
        'headers_info': {
            'Content-Security-Policy': 'Prevents XSS attacks',
            'X-Frame-Options': 'Prevents clickjacking',
            'X-Content-Type-Options': 'Prevents MIME sniffing',
            'X-XSS-Protection': 'Browser XSS protection',
            'Strict-Transport-Security': 'Enforces HTTPS (if enabled)'
        }
    })

# =============================================================================
# MAINTENANCE AND MONITORING EXAMPLES
# =============================================================================

@app.route('/api/admin/security-status')
@token_required
@admin_required
@admin_rate_limit
def security_status():
    """Get security system status (admin only)"""
    return jsonify({
        'rate_limiter': {
            'active_clients': len(rate_limiter.requests),
            'status': 'operational'
        },
        'auth_middleware': {
            'status': 'operational',
            'jwt_algorithm': app.config.get('JWT_ALGORITHM', 'HS256')
        },
        'security_headers': {
            'status': 'operational',
            'csp_enabled': True
        }
    })

@app.route('/api/admin/cleanup', methods=['POST'])
@token_required
@admin_required
@strict_rate_limit
def cleanup_security():
    """Cleanup security middleware (admin only)"""
    cleanup_rate_limiter()
    
    return jsonify({
        'message': 'Security middleware cleaned up successfully'
    })

# =============================================================================
# ERROR HANDLING EXAMPLES
# =============================================================================

@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit exceeded errors"""
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': 'Too many requests. Please try again later.',
        'retry_after': getattr(error, 'retry_after', 60)
    }), 429

@app.errorhandler(401)
def unauthorized(error):
    """Handle authentication errors"""
    return jsonify({
        'error': 'Authentication required',
        'message': 'Please provide a valid token'
    }), 401

@app.errorhandler(403)
def forbidden(error):
    """Handle authorization errors"""
    return jsonify({
        'error': 'Access forbidden',
        'message': 'Insufficient permissions'
    }), 403

# =============================================================================
# INTEGRATION EXAMPLE
# =============================================================================

@app.route('/api/complete-example', methods=['POST'])
@rate_limit(requests_per_minute=20, requests_per_hour=200)
@token_required
@permission_required('write_content')
def complete_security_example():
    """
    Complete example combining multiple security features:
    - Rate limiting
    - Authentication
    - Permission checking
    - Input validation
    - Output sanitization
    """
    data = request.get_json()
    
    # Validate required fields
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400
    
    # Validate input lengths
    if not validate_input_length(title, max_length=100):
        return jsonify({'error': 'Title too long (max 100 characters)'}), 400
    
    if not validate_input_length(content, max_length=1000):
        return jsonify({'error': 'Content too long (max 1000 characters)'}), 400
    
    # Sanitize inputs
    safe_title = escape_html(title)
    safe_content = escape_html(content)
    
    # Get current user info
    user = g.current_user
    
    # Here you would save to database
    # For demo, we'll just return the processed data
    
    return jsonify({
        'message': 'Content created successfully',
        'data': {
            'title': safe_title,
            'content': safe_content,
            'author_id': user.get('user_id'),
            'created_at': '2025-07-22T14:00:00Z'
        },
        'security_info': {
            'rate_limit_status': get_rate_limit_status(),
            'user_permissions': get_user_permissions(),
            'csp_nonce': get_csp_nonce()
        }
    })

if __name__ == '__main__':
    # Development configuration
    app.config['JWT_SECRET_KEY'] = 'development-secret-change-in-production'
    app.config['JWT_EXPIRATION_HOURS'] = 24
    
    # Enable debug mode for development
    app.run(debug=True, host='0.0.0.0', port=5000)
