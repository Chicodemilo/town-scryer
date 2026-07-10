# ==============================================================================
# File:      api/app/security/security_headers.py
# Purpose:   Security headers middleware. Adds CSP, HSTS, X-Frame-Options,
#            and other protective headers to every response. Also provides
#            utility functions for URL safety, password hashing, filename
#            sanitization, and HTML escaping.
# Callers:   security/__init__.py, app/__init__.py
# Callees:   Flask, secrets, hashlib, html, re, os
# Modified:  2026-04-22
# ==============================================================================
"""
Security Headers Middleware for Flask API

Adds essential security headers to all responses to protect against
common web vulnerabilities and attacks.
"""

from flask import request, g
import secrets
import hashlib
import re

class SecurityHeaders:
    """
    Middleware to add security headers to all responses
    """
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security headers middleware with Flask app"""
        self.app = app
        
        # Default security configuration
        app.config.setdefault('SECURITY_HEADERS', {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'X-Permitted-Cross-Domain-Policies': 'none',
            'Cross-Origin-Embedder-Policy': 'require-corp',
            'Cross-Origin-Opener-Policy': 'same-origin',
            'Cross-Origin-Resource-Policy': 'same-origin'
        })
        
        # HSTS configuration
        app.config.setdefault('HSTS_MAX_AGE', 31536000)  # 1 year
        app.config.setdefault('HSTS_INCLUDE_SUBDOMAINS', True)
        app.config.setdefault('HSTS_PRELOAD', True)
        
        # CSP configuration
        app.config.setdefault('CSP_POLICY', {
            'default-src': ["'self'"],
            'script-src': ["'self'", "'unsafe-inline'"],
            'style-src': ["'self'", "'unsafe-inline'"],
            'img-src': ["'self'", "data:", "https:"],
            'font-src': ["'self'"],
            'connect-src': ["'self'"],
            'media-src': ["'self'"],
            'object-src': ["'none'"],
            'child-src': ["'self'"],
            'frame-ancestors': ["'none'"],
            'form-action': ["'self'"],
            'base-uri': ["'self'"],
            'manifest-src': ["'self'"]
        })
        
        # CORS configuration
        app.config.setdefault('CORS_ORIGINS', ['http://localhost:3151', 'http://localhost:5151'])
        app.config.setdefault('CORS_METHODS', ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
        app.config.setdefault('CORS_HEADERS', ['Content-Type', 'Authorization', 'X-API-Key'])
        
        # Register after_request handler
        app.after_request(self.add_security_headers)
        
        # Register before_request handler for CORS preflight
        app.before_request(self.handle_preflight)
    
    def generate_nonce(self):
        """Generate a cryptographically secure nonce for CSP"""
        return secrets.token_urlsafe(16)
    
    def build_csp_header(self, nonce=None):
        """
        Build Content Security Policy header
        
        Args:
            nonce (str): Optional nonce for inline scripts/styles
            
        Returns:
            str: CSP header value
        """
        csp_policy = self.app.config['CSP_POLICY'].copy()
        
        # Add nonce to script-src and style-src if provided
        if nonce:
            if 'script-src' in csp_policy:
                csp_policy['script-src'] = csp_policy['script-src'] + [f"'nonce-{nonce}'"]
            if 'style-src' in csp_policy:
                csp_policy['style-src'] = csp_policy['style-src'] + [f"'nonce-{nonce}'"]
        
        # Build CSP string
        csp_parts = []
        for directive, sources in csp_policy.items():
            if isinstance(sources, list):
                sources_str = ' '.join(sources)
            else:
                sources_str = sources
            csp_parts.append(f"{directive} {sources_str}")
        
        return '; '.join(csp_parts)
    
    def handle_preflight(self):
        """Handle CORS preflight requests"""
        if request.method == 'OPTIONS':
            response = self.app.make_default_options_response()
            return self.add_cors_headers(response)
    
    def add_cors_headers(self, response):
        """
        Add CORS headers to response
        
        Args:
            response: Flask response object
            
        Returns:
            Flask response object with CORS headers
        """
        origin = request.headers.get('Origin')
        allowed_origins = self.app.config['CORS_ORIGINS']
        
        # Check if origin is allowed
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
        elif '*' in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = '*'
        
        response.headers['Access-Control-Allow-Methods'] = ', '.join(self.app.config['CORS_METHODS'])
        response.headers['Access-Control-Allow-Headers'] = ', '.join(self.app.config['CORS_HEADERS'])
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '86400'  # 24 hours
        
        return response
    
    def add_security_headers(self, response):
        """
        Add security headers to response
        
        Args:
            response: Flask response object
            
        Returns:
            Flask response object with security headers
        """
        # Add CORS headers
        response = self.add_cors_headers(response)
        
        # Add basic security headers
        security_headers = self.app.config['SECURITY_HEADERS']
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Add HSTS header for HTTPS
        if request.is_secure:
            hsts_value = f"max-age={self.app.config['HSTS_MAX_AGE']}"
            if self.app.config['HSTS_INCLUDE_SUBDOMAINS']:
                hsts_value += "; includeSubDomains"
            if self.app.config['HSTS_PRELOAD']:
                hsts_value += "; preload"
            response.headers['Strict-Transport-Security'] = hsts_value
        
        # Add CSP header
        nonce = getattr(g, 'csp_nonce', None)
        csp_header = self.build_csp_header(nonce)
        response.headers['Content-Security-Policy'] = csp_header
        
        # Add additional security headers based on content type
        if response.content_type and 'application/json' in response.content_type:
            response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Remove server header for security
        response.headers.pop('Server', None)
        
        return response

def generate_csp_nonce():
    """
    Generate and store CSP nonce in request context
    
    Returns:
        str: Generated nonce
    """
    nonce = secrets.token_urlsafe(16)
    g.csp_nonce = nonce
    return nonce

def get_csp_nonce():
    """
    Get CSP nonce from request context
    
    Returns:
        str: CSP nonce or None
    """
    return getattr(g, 'csp_nonce', None)

# Security utility functions
def is_safe_url(target):
    """
    Check if URL is safe for redirects
    
    Args:
        target (str): URL to check
        
    Returns:
        bool: True if URL is safe
    """
    if not target:
        return False
    
    # Basic checks for safe URLs
    if target.startswith('//') or target.startswith('http://') or target.startswith('https://'):
        return False
    
    if target.startswith('/') and not target.startswith('//'):
        return True
    
    return False

def hash_password(password, salt=None):
    """
    Hash password with salt
    
    Args:
        password (str): Password to hash
        salt (str): Optional salt (generates if not provided)
        
    Returns:
        tuple: (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(32)
    
    # Use PBKDF2 with SHA-256
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return hashed.hex(), salt

def verify_password(password, hashed_password, salt):
    """
    Verify password against hash
    
    Args:
        password (str): Password to verify
        hashed_password (str): Stored hash
        salt (str): Salt used for hashing
        
    Returns:
        bool: True if password matches
    """
    test_hash, _ = hash_password(password, salt)
    return test_hash == hashed_password

def sanitize_filename(filename):
    """
    Sanitize filename for safe storage
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    import re
    import os
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    
    return filename

def validate_input_length(value, max_length=1000):
    """
    Validate input length to prevent DoS attacks
    
    Args:
        value (str): Input value
        max_length (int): Maximum allowed length
        
    Returns:
        bool: True if length is valid
    """
    return len(str(value)) <= max_length

def escape_html(text):
    """
    Escape HTML characters to prevent XSS
    
    Args:
        text (str): Text to escape
        
    Returns:
        str: Escaped text
    """
    import html
    return html.escape(str(text))

def sanitize_text(value, max_length=None):
    """
    Sanitize text input by stripping HTML tags and enforcing max length.

    Args:
        value: Input value to sanitize
        max_length (int): Optional maximum length to enforce

    Returns:
        str: Sanitized text
    """
    if value is None:
        return ''
    text = re.sub(r'<[^>]*>', '', str(value))
    text = text.strip()
    if max_length is not None:
        text = text[:max_length]
    return text


# Global security headers instance
security_headers = SecurityHeaders()
