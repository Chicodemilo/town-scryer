# ==============================================================================
# File:      api/app/config/settings.py
# Purpose:   Central application configuration loaded from environment
#            variables. Covers database, JWT, admin seed credentials, SMTP,
#            CORS origins, and security header defaults.
# Callers:   app/__init__.py, config/__init__.py
# Callees:   os (stdlib)
# Modified:  2026-04-22
# ==============================================================================
import os


class Config:
    """Application configuration from environment variables"""

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.getenv('SECRET_KEY', 'dev-secret-key'))
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

    # Admin seed
    ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'change_me_admin_password')

    # App
    APP_NAME = os.getenv('APP_NAME', 'Town Scryer')
    APP_ENV = os.getenv('APP_ENV', 'development')

    # Frontend URL (for email verification links)
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3151')

    # SMTP (optional — logs to console if not set)
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
    SMTP_FROM_EMAIL = os.getenv('SMTP_FROM_EMAIL')

    # CORS
    CORS_ORIGINS = [
        'http://localhost:3151',
        'http://localhost:3152',
        'http://localhost:5151',
        'http://localhost:8081',
        'http://127.0.0.1:3151',
        'http://127.0.0.1:3152',
        'http://127.0.0.1:5151',
        'http://127.0.0.1:8081',
    ]

    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
