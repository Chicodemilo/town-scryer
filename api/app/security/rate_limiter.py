# ==============================================================================
# File:      api/app/security/rate_limiter.py
# Purpose:   Rate limiting middleware using a sliding-window algorithm.
#            Provides configurable per-endpoint decorators (strict,
#            moderate, lenient, admin) and cleanup utilities.
# Callers:   security/__init__.py, app/__init__.py
# Callees:   Flask, time, json, functools, collections, threading, datetime
# Modified:  2026-04-22
# ==============================================================================
"""
Rate Limiting Middleware for Flask API

Provides configurable rate limiting to prevent abuse and ensure API stability.
Supports different rate limits for different endpoints and user types.
"""

import os
import time
import json
from functools import wraps
from collections import defaultdict, deque
from flask import request, jsonify, g
from datetime import datetime, timedelta
import threading

def _rate_limit_disabled():
    return os.getenv('RATE_LIMIT_DISABLED', '').lower() in ('true', '1', 'yes')

class RateLimiter:
    """
    Thread-safe rate limiter using sliding window algorithm
    """
    
    def __init__(self):
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()
        
    def is_allowed(self, key, limit, window_seconds):
        """
        Check if request is allowed based on rate limit
        
        Args:
            key (str): Unique identifier for the client (IP, user_id, etc.)
            limit (int): Maximum number of requests allowed
            window_seconds (int): Time window in seconds
            
        Returns:
            tuple: (is_allowed: bool, retry_after: int)
        """
        now = time.time()
        window_start = now - window_seconds
        
        with self.lock:
            # Remove old requests outside the window
            while self.requests[key] and self.requests[key][0] < window_start:
                self.requests[key].popleft()
            
            # Check if limit exceeded
            if len(self.requests[key]) >= limit:
                # Calculate retry after time
                oldest_request = self.requests[key][0]
                retry_after = int(oldest_request + window_seconds - now) + 1
                return False, retry_after
            
            # Add current request
            self.requests[key].append(now)
            return True, 0
    
    def cleanup_old_entries(self, max_age_seconds=3600):
        """
        Clean up old entries to prevent memory leaks
        Should be called periodically
        """
        cutoff = time.time() - max_age_seconds
        
        with self.lock:
            keys_to_remove = []
            for key, requests in self.requests.items():
                # Remove old requests
                while requests and requests[0] < cutoff:
                    requests.popleft()
                
                # Remove empty entries
                if not requests:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.requests[key]

# Global rate limiter instance
rate_limiter = RateLimiter()

def get_client_identifier():
    """
    Get unique identifier for the client
    Priority: user_id > api_key > ip_address
    """
    # Check for authenticated user
    if hasattr(g, 'current_user') and g.current_user:
        return f"user_{g.current_user.get('id', 'unknown')}"
    
    # Check for API key
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return f"api_{api_key[:8]}"  # Use first 8 chars for privacy
    
    # Fall back to IP address
    # Handle proxy headers
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return f"ip_{forwarded_for.split(',')[0].strip()}"
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return f"ip_{real_ip}"
    
    return f"ip_{request.remote_addr}"

def rate_limit(requests_per_minute=60, requests_per_hour=1000, per_user_multiplier=2):
    """
    Rate limiting decorator
    
    Args:
        requests_per_minute (int): Requests allowed per minute
        requests_per_hour (int): Requests allowed per hour  
        per_user_multiplier (int): Multiplier for authenticated users
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import current_app
            if current_app.config.get('TESTING') or _rate_limit_disabled():
                return f(*args, **kwargs)
            client_id = get_client_identifier()
            
            # Apply multiplier for authenticated users
            minute_limit = requests_per_minute
            hour_limit = requests_per_hour
            
            if client_id.startswith('user_'):
                minute_limit *= per_user_multiplier
                hour_limit *= per_user_multiplier
            
            # Check minute limit
            allowed, retry_after = rate_limiter.is_allowed(
                f"{client_id}_minute", minute_limit, 60
            )
            
            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Try again in {retry_after} seconds.',
                    'retry_after': retry_after,
                    'limit': minute_limit,
                    'window': '1 minute'
                }), 429
            
            # Check hour limit
            allowed, retry_after = rate_limiter.is_allowed(
                f"{client_id}_hour", hour_limit, 3600
            )
            
            if not allowed:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Hourly limit exceeded. Try again in {retry_after} seconds.',
                    'retry_after': retry_after,
                    'limit': hour_limit,
                    'window': '1 hour'
                }), 429
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Predefined rate limit decorators for common use cases
def strict_rate_limit(f):
    """Very strict rate limiting for sensitive endpoints"""
    return rate_limit(requests_per_minute=10, requests_per_hour=100)(f)

def moderate_rate_limit(f):
    """Moderate rate limiting for general API endpoints"""
    return rate_limit(requests_per_minute=30, requests_per_hour=500)(f)

def lenient_rate_limit(f):
    """Lenient rate limiting for public endpoints"""
    return rate_limit(requests_per_minute=100, requests_per_hour=2000)(f)

def admin_rate_limit(f):
    """Higher limits for admin endpoints"""
    return rate_limit(requests_per_minute=200, requests_per_hour=5000, per_user_multiplier=1)(f)

def get_rate_limit_status(client_id=None):
    """
    Get current rate limit status for debugging
    
    Args:
        client_id (str): Client identifier (optional, uses current client if not provided)
        
    Returns:
        dict: Rate limit status information
    """
    if not client_id:
        client_id = get_client_identifier()
    
    now = time.time()
    
    # Count requests in last minute and hour
    minute_requests = len([
        req for req in rate_limiter.requests.get(f"{client_id}_minute", [])
        if req > now - 60
    ])
    
    hour_requests = len([
        req for req in rate_limiter.requests.get(f"{client_id}_hour", [])
        if req > now - 3600
    ])
    
    return {
        'client_id': client_id,
        'requests_last_minute': minute_requests,
        'requests_last_hour': hour_requests,
        'timestamp': datetime.now().isoformat()
    }

# Cleanup task (should be run periodically)
def cleanup_rate_limiter():
    """Clean up old rate limiter entries"""
    rate_limiter.cleanup_old_entries()
