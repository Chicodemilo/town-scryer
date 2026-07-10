# ==============================================================================
# File:      api/app/routes/admin.py
# Purpose:   Admin route blueprint. Provides endpoints for user management,
#            terms & conditions, admin invites, permissions, health checks,
#            analytics, and test results.
# Callers:   routes/__init__.py
# Callees:   models/user.py, models/page_hit.py, services/auth_service.py,
#            security/__init__.py, Flask, db
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, request, jsonify, g
from app import db
from app.models.user import User
from app.services.auth_service import AuthService
from app.security import auth_middleware, admin_rate_limit, lenient_rate_limit, token_required, admin_required, moderate_rate_limit
from datetime import datetime, timedelta
import logging
import json
import os

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)


@admin_bp.route('/login', methods=['POST'])
@moderate_rate_limit
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({'success': False, 'message': 'Username and password are required'}), 400

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        if not user or not user.check_password(password):
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

        if not user.is_admin:
            return jsonify({'success': False, 'message': 'Insufficient privileges'}), 403

        token = auth_middleware.generate_token(user.to_dict())

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Admin login error: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@admin_bp.route('/tables', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def list_tables_admin():
    """List every game_table with the scene_model setting exposed so the
    admin can A/B model assignments without surfacing the choice to DMs."""
    from app.models.game_table import GameTable as GT
    from app.models.session import Session as SessionModel
    tables = GT.query.order_by(GT.created_at.desc()).limit(200).all()
    results = []
    for t in tables:
        owner = User.query.get(t.owner_user_id)
        session_count = SessionModel.query.filter_by(table_id=t.id).count()
        results.append({
            'id': t.id,
            'name': t.name,
            'owner_username': owner.username if owner else None,
            'scene_model': t.scene_model,
            'image_model': t.image_model,
            'session_count': session_count,
            'created_at': t.created_at.isoformat() if t.created_at else None,
        })
    return jsonify({'success': True, 'tables': results}), 200


@admin_bp.route('/tables/<int:table_id>/scene-model', methods=['PUT'])
@admin_rate_limit
@token_required
@admin_required
def set_table_scene_model(table_id):
    """Admin-only override of scene_model for a specific table."""
    from app.models.game_table import GameTable as GT
    table = GT.query.get(table_id)
    if not table:
        return jsonify({'success': False, 'message': 'Table not found'}), 404
    data = request.get_json() or {}
    sm = (data.get('scene_model') or '').strip()
    table.scene_model = sm or None
    db.session.commit()
    return jsonify({'success': True, 'scene_model': table.scene_model}), 200


@admin_bp.route('/tables/<int:table_id>/image-model', methods=['PUT'])
@admin_rate_limit
@token_required
@admin_required
def set_table_image_model(table_id):
    """Admin-only override of image_model (fal endpoint) for a specific table."""
    from app.models.game_table import GameTable as GT
    table = GT.query.get(table_id)
    if not table:
        return jsonify({'success': False, 'message': 'Table not found'}), 404
    data = request.get_json() or {}
    im = (data.get('image_model') or '').strip()
    table.image_model = im or None
    db.session.commit()
    return jsonify({'success': True, 'image_model': table.image_model}), 200


@admin_bp.route('/sessions', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def list_sessions():
    """List all sessions with quality scores for the admin Sessions view.

    Sorted by quality_score DESC by default (worst-first) so problem
    sessions surface immediately. Optional ?sort=recent flips to started_at
    DESC."""
    from app.models.session import Session as SessionModel
    from app.models.game_table import GameTable as GT

    sort = request.args.get('sort', 'quality')
    limit = min(int(request.args.get('limit', 100)), 500)

    q = SessionModel.query
    if sort == 'recent':
        q = q.order_by(SessionModel.started_at.desc())
    else:
        q = q.order_by(SessionModel.quality_score.desc(),
                       SessionModel.started_at.desc())

    sessions = q.limit(limit).all()
    results = []
    for s in sessions:
        owner = User.query.get(s.user_id)
        table = GT.query.get(s.table_id) if s.table_id else None
        # Duration in seconds — uses ended_at if present, otherwise now.
        end = s.ended_at or datetime.utcnow()
        duration_s = int((end - s.started_at).total_seconds()) if s.started_at else 0
        results.append({
            'id': s.id,
            'user_id': s.user_id,
            'username': owner.username if owner else None,
            'table_id': s.table_id,
            'table_name': table.name if table else None,
            'status': s.status,
            'quality_score': s.quality_score or 0,
            'scene_model': s.scene_model,
            'audit_count': s.audit_count or 0,
            'audit_retry_count': s.audit_retry_count or 0,
            'image_count': s.image_count or 0,
            'regen_count': s.regen_count or 0,
            'api_call_count': s.api_call_count or 0,
            'estimated_cost_cents': s.estimated_cost_cents or 0,
            'duration_s': duration_s,
            'game_type': s.game_type,
            'art_style': s.art_style,
            'rating': s.rating,
            'started_at': s.started_at.isoformat() if s.started_at else None,
            'ended_at': s.ended_at.isoformat() if s.ended_at else None,
        })
    return jsonify({'success': True, 'sessions': results}), 200


@admin_bp.route('/stats', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def admin_stats():
    """Get admin dashboard statistics"""
    try:
        user_count = User.query.count()

        # Recent signups (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_users = User.query.filter(User.created_at >= week_ago).count()

        return jsonify({
            'success': True,
            'stats': {
                'users': user_count,
                'recent_signups': recent_users
            }
        }), 200

    except Exception as e:
        logger.error(f"Admin stats error: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@admin_bp.route('/users', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def list_users():
    """List all users with search/filter"""
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )

    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=min(per_page, 100), error_out=False)

    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'pages': pagination.pages
    }), 200


@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def get_user(user_id):
    """Get user detail"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'user': user.to_dict(),
    }), 200


@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_rate_limit
@token_required
@admin_required
def update_user(user_id):
    """Update user (toggle admin, etc.)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if 'is_admin' in data:
        user.is_admin = data['is_admin']
    if 'email_verified' in data:
        user.email_verified = data['email_verified']

    db.session.commit()
    return jsonify({'user': user.to_dict()}), 200


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_rate_limit
@token_required
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Prevent deleting yourself
    if user.id == g.current_user.get('user_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400

    db.session.delete(user)
    db.session.commit()
    logger.info(f"Admin deleted user: {user.username}")
    return jsonify({'message': 'User deleted'}), 200


# --- Terms & Conditions ---

@admin_bp.route('/terms', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def admin_get_terms():
    terms = AuthService.get_terms()
    return jsonify({'terms': terms.to_dict()}), 200


@admin_bp.route('/terms', methods=['PUT'])
@admin_rate_limit
@token_required
@admin_required
def admin_update_terms():
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': 'Content required'}), 400
    terms = AuthService.update_terms(data['content'], g.current_user.get('user_id'))
    return jsonify({'terms': terms.to_dict(), 'message': 'Terms updated'}), 200


@admin_bp.route('/terms/reset', methods=['POST'])
@admin_rate_limit
@token_required
@admin_required
def admin_reset_terms():
    AuthService.reset_all_terms()
    return jsonify({'message': 'All users must re-accept terms'}), 200


# --- Admin Invite ---

@admin_bp.route('/invite', methods=['POST'])
@admin_rate_limit
@token_required
@admin_required
def admin_invite_user():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Email required'}), 400
    user, error = AuthService.invite_user(data['email'], g.current_user.get('user_id'))
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'user': user.to_dict(), 'message': 'Invite sent'}), 201


# --- Admin Users Management ---

@admin_bp.route('/admin-users', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def list_admin_users():
    admins = AuthService.get_admin_users()
    return jsonify({'users': [u.to_dict() for u in admins]}), 200


# --- Admin Permissions ---

@admin_bp.route('/users/<int:user_id>/permissions', methods=['PUT'])
@admin_rate_limit
@token_required
@admin_required
def update_user_permissions(user_id):
    data = request.get_json()
    if not data or 'permissions' not in data:
        return jsonify({'error': 'Permissions object required'}), 400
    user, error = AuthService.update_admin_permissions(user_id, data['permissions'])
    if error:
        return jsonify({'error': error}), 400
    return jsonify({'user': user.to_dict()}), 200


# --- Health & Test Results ---

@admin_bp.route('/health', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def admin_health():
    from app import db as _db
    try:
        with _db.engine.connect() as conn:
            conn.execute(_db.text('SELECT 1'))
        db_status = 'connected'
    except Exception:
        db_status = 'disconnected'

    return jsonify({
        'api_status': 'running',
        'database': db_status,
        'users': User.query.count(),
        'timestamp': datetime.utcnow().isoformat(),
    }), 200


@admin_bp.route('/test-results', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def admin_test_results():
    results_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'test-results.json')
    if not os.path.exists(results_path):
        return jsonify({'error': 'No test results available', 'results': None}), 200
    try:
        with open(results_path, 'r') as f:
            results = json.load(f)
        return jsonify({'results': results}), 200
    except Exception:
        return jsonify({'error': 'Failed to read test results', 'results': None}), 200


# --- Page Hit Analytics ---

@admin_bp.route('/hit', methods=['POST'])
@lenient_rate_limit
def record_hit():
    """Record a page hit (public, no auth required)."""
    try:
        from app.models.page_hit import PageHit

        data = request.get_json(silent=True) or {}
        path = data.get('path', '/')
        if not path or len(path) > 255:
            return '', 204

        # Extract IP: prefer X-Forwarded-For / X-Real-IP (behind nginx)
        ip_address = (
            request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            or request.headers.get('X-Real-IP', '')
            or request.remote_addr
        )

        referrer = data.get('referrer') or request.referrer or None
        if referrer and len(referrer) > 500:
            referrer = referrer[:500]

        user_agent = request.headers.get('User-Agent', '')
        if len(user_agent) > 500:
            user_agent = user_agent[:500]

        # Auto-block if this IP has any existing blocked hits
        is_blocked = False
        if ip_address:
            existing_blocked = PageHit.query.filter_by(
                ip_address=ip_address, blocked=True
            ).first()
            if existing_blocked:
                is_blocked = True

        hit = PageHit(
            path=path,
            ip_address=ip_address,
            referrer=referrer,
            user_agent=user_agent,
            blocked=is_blocked,
        )
        db.session.add(hit)
        db.session.commit()

        return '', 204

    except Exception as e:
        logger.error(f"Record hit error: {str(e)}")
        db.session.rollback()
        return '', 204  # Fail silently — analytics should never break UX


@admin_bp.route('/analytics', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def get_analytics():
    """Get page hit analytics. Query params: days (default 30), hide_blocked (default true)."""
    try:
        from app.models.page_hit import PageHit
        from sqlalchemy import func

        days = request.args.get('days', 30, type=int)
        if days < 1:
            days = 1
        if days > 365:
            days = 365

        hide_blocked = request.args.get('hide_blocked', 'true').lower() != 'false'

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Base filters applied to all queries
        base_filters = [PageHit.created_at >= cutoff]
        if hide_blocked:
            base_filters.append(PageHit.blocked == False)

        # Total hits per path
        hits_per_path = db.session.query(
            PageHit.path,
            func.count(PageHit.id).label('total_hits'),
            func.count(func.distinct(PageHit.ip_address)).label('unique_ips'),
        ).filter(
            *base_filters
        ).group_by(PageHit.path).order_by(func.count(PageHit.id).desc()).all()

        path_stats = [
            {'path': row.path, 'total_hits': row.total_hits, 'unique_ips': row.unique_ips}
            for row in hits_per_path
        ]

        # Hits by day — total
        hits_by_day = db.session.query(
            func.date(PageHit.created_at).label('day'),
            func.count(PageHit.id).label('hits'),
        ).filter(
            *base_filters
        ).group_by(func.date(PageHit.created_at)).order_by(func.date(PageHit.created_at)).all()

        daily_stats = [
            {'date': str(row.day), 'hits': row.hits}
            for row in hits_by_day
        ]

        # Hits by day per path (for multi-line chart)
        hits_by_day_path = db.session.query(
            func.date(PageHit.created_at).label('day'),
            PageHit.path,
            func.count(PageHit.id).label('hits'),
        ).filter(
            *base_filters
        ).group_by(func.date(PageHit.created_at), PageHit.path).order_by(func.date(PageHit.created_at)).all()

        daily_by_path = {}
        for row in hits_by_day_path:
            path = row.path
            if path not in daily_by_path:
                daily_by_path[path] = []
            daily_by_path[path].append({'date': str(row.day), 'hits': row.hits})

        # Top 10 referrers (excluding empty/self)
        referrer_filters = base_filters + [
            PageHit.referrer.isnot(None),
            PageHit.referrer != '',
        ]
        top_referrers = db.session.query(
            PageHit.referrer,
            func.count(PageHit.id).label('count'),
        ).filter(
            *referrer_filters
        ).group_by(PageHit.referrer).order_by(func.count(PageHit.id).desc()).limit(10).all()

        referrer_stats = [
            {'referrer': row.referrer, 'count': row.count}
            for row in top_referrers
        ]

        # Recent 50 hits
        recent = PageHit.query.filter(
            *base_filters
        ).order_by(PageHit.created_at.desc()).limit(50).all()

        return jsonify({
            'success': True,
            'days': days,
            'hide_blocked': hide_blocked,
            'path_stats': path_stats,
            'daily_stats': daily_stats,
            'daily_by_path': daily_by_path,
            'top_referrers': referrer_stats,
            'recent_hits': [h.to_dict() for h in recent],
        }), 200

    except Exception as e:
        logger.error(f"Analytics error: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@admin_bp.route('/analytics/block-ip', methods=['POST'])
@admin_rate_limit
@token_required
@admin_required
def block_ip():
    """Block or unblock all hits from an IP address."""
    try:
        from app.models.page_hit import PageHit

        data = request.get_json()
        if not data or not data.get('ip'):
            return jsonify({'success': False, 'message': 'IP address required'}), 400

        ip = data['ip'].strip()
        if not ip or len(ip) > 45:
            return jsonify({'success': False, 'message': 'Invalid IP address'}), 400

        blocked = data.get('blocked', True)

        affected = PageHit.query.filter_by(ip_address=ip).update({'blocked': blocked})
        db.session.commit()

        action = 'blocked' if blocked else 'unblocked'
        logger.info(f"Admin {action} IP {ip} — {affected} hits affected")

        return jsonify({
            'success': True,
            'ip': ip,
            'blocked': blocked,
            'affected_rows': affected,
        }), 200

    except Exception as e:
        logger.error(f"Block IP error: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Server error'}), 500


@admin_bp.route('/analytics/blocked-ips', methods=['GET'])
@admin_rate_limit
@token_required
@admin_required
def get_blocked_ips():
    """Return distinct IPs that have blocked hits."""
    try:
        from app.models.page_hit import PageHit
        from sqlalchemy import func

        blocked_ips = db.session.query(
            PageHit.ip_address,
            func.count(PageHit.id).label('hit_count'),
        ).filter(
            PageHit.blocked == True,
            PageHit.ip_address.isnot(None),
        ).group_by(PageHit.ip_address).order_by(func.count(PageHit.id).desc()).all()

        return jsonify({
            'success': True,
            'blocked_ips': [
                {'ip': row.ip_address, 'hit_count': row.hit_count}
                for row in blocked_ips
            ],
        }), 200

    except Exception as e:
        logger.error(f"Blocked IPs error: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500
