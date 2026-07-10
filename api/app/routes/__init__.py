# ==============================================================================
# File:      api/app/routes/__init__.py
# Purpose:   Package init for routes. Imports all blueprint modules and
#            provides register_blueprints() to mount them on the Flask app.
# Callers:   app/__init__.py
# Callees:   routes/auth.py, routes/admin.py, routes/uploads.py, routes/logs.py,
#            routes/sessions.py, routes/preferences.py, routes/history.py,
#            routes/tables.py, routes/characters.py
# Modified:  2026-06-01
# ==============================================================================
from .auth import auth_bp
from .admin import admin_bp
from .uploads import uploads_bp
from .logs import logs_bp
from .sessions import sessions_bp
from .preferences import preferences_bp
from .history import history_bp
from .tables import tables_bp
from .characters import characters_bp
from .npcs import npcs_bp


def register_blueprints(app):
    """Register all blueprints with the Flask app"""
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(uploads_bp, url_prefix='/api/uploads')
    app.register_blueprint(logs_bp, url_prefix='/api/logs')
    app.register_blueprint(sessions_bp, url_prefix='/api/session')
    app.register_blueprint(preferences_bp, url_prefix='/api/preferences')
    app.register_blueprint(history_bp, url_prefix='/api/sessions')
    app.register_blueprint(tables_bp, url_prefix='/api/tables')
    app.register_blueprint(characters_bp, url_prefix='/api/tables')
    app.register_blueprint(npcs_bp, url_prefix='/api/tables')
