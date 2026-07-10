# ==============================================================================
# File:      api/app/routes/sessions.py
# Purpose:   Session route blueprint. Handles session lifecycle (start, pause,
#            resume, end, heartbeat), transcript chunk processing for scene
#            extraction, and session queries (current, latest scene).
# Callers:   routes/__init__.py
# Callees:   services/session_service.py, services/scene_service.py,
#            security/__init__.py, Flask
# Modified:  2026-06-01
# ==============================================================================
from flask import Blueprint, jsonify, request, g
from app.services.session_service import SessionService
from app.services.scene_service import analyze_transcript_chunk
from app.services.transcription_service import transcribe_audio
from app.services.image_gen import generate_image
from app.services.rate_limiter_service import RateLimiterService
from app.models.scene import Scene
from app.models.game_table import GameTable
from app.models.session_correction import SessionCorrection
from app.security import token_required
from app import db
import logging

sessions_bp = Blueprint('sessions', __name__)
logger = logging.getLogger('security')


@sessions_bp.route('/start', methods=['POST'])
@token_required
def start_session():
    user_id = g.current_user.get('user_id')

    # Monthly rate-limit checks
    limit_error, limit_status = RateLimiterService.check_session_start_limits(user_id)
    if limit_error:
        return jsonify({'error': limit_error}), limit_status

    data = request.get_json(silent=True) or {}

    game_type = data.get('game_type')
    art_style = data.get('art_style')
    rating = data.get('rating')
    table_id = data.get('table_id')
    show_captions = data.get('show_captions')  # None if client omitted

    # If table_id provided, validate current user is the table owner (DM)
    if table_id is not None:
        table = GameTable.query.get(table_id)
        if not table:
            return jsonify({'error': 'Table not found'}), 404
        if table.owner_user_id != user_id:
            return jsonify({'error': 'Only the table owner (DM) can run sessions'}), 403

    session, error = SessionService.start_session(
        user_id, game_type=game_type, art_style=art_style,
        rating=rating, table_id=table_id, show_captions=show_captions
    )
    if error:
        return jsonify({'error': error}), 409

    # Increment monthly session counter on successful start
    RateLimiterService.increment_monthly_session_count(user_id)

    return jsonify({
        'session_token': session.session_token,
        'session_id': session.id,
        'status': session.status,
        'game_type': session.game_type,
        'art_style': session.art_style,
        'rating': session.rating,
    }), 201


@sessions_bp.route('/pause', methods=['POST'])
@token_required
def pause_session():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token'):
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.pause_session(user_id, data['session_token'])
    if error:
        return jsonify({'error': error}), 400

    return jsonify({'status': 'paused'}), 200


@sessions_bp.route('/resume', methods=['POST'])
@token_required
def resume_session():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token'):
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.resume_session(user_id, data['session_token'])
    if error:
        return jsonify({'error': error}), 400

    return jsonify({'status': 'active'}), 200


@sessions_bp.route('/end', methods=['POST'])
@token_required
def end_session():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token'):
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.end_session(user_id, data['session_token'])
    if error:
        return jsonify({'error': error}), 400

    duration_seconds = int(
        (session.ended_at - session.started_at).total_seconds()
    )
    return jsonify({
        'status': 'ended',
        'image_count': session.image_count,
        'duration_seconds': duration_seconds,
    }), 200


@sessions_bp.route('/heartbeat', methods=['POST'])
@token_required
def heartbeat():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token'):
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.heartbeat(user_id, data['session_token'])
    if error:
        return jsonify({'error': error}), 400

    return jsonify({'status': 'ok'}), 200


def _analyze_and_respond(session, transcript: str):
    """Shared chunk-analysis flow. Used by both the text /chunk and the audio
    /audio-chunk endpoints. Returns a Flask response tuple."""
    if session.status != 'active':
        # Not an error: a chunk arrived after the DM hit Pause, which is a
        # normal race during the ~30s upload window. Return 200 so the
        # frontend doesn't flag it as a failure, with a flag the client can
        # use if it ever wants to surface "ignored while paused" state.
        return jsonify({
            'scene_changed': False,
            'scene_description': None,
            'image_url': None,
            'ignored': True,
            'reason': f'session_{session.status}',
        }), 200

    limit_result = RateLimiterService.check_chunk_limits(session)
    if limit_result:
        if limit_result.get('force_paused'):
            return jsonify(limit_result), 200
        try:
            result = analyze_transcript_chunk(session, transcript, skip_image=True)
        except Exception as e:
            logger.error(f'Scene analysis failed: {e}')
            return jsonify({'error': 'Scene analysis failed'}), 500

        response = {
            'scene_changed': result['scene_changed'],
            'scene_description': result['scene_description'],
            'image_url': None,
            'transcript': transcript,
        }
        response.update(limit_result)
        return jsonify(response), 200

    try:
        result = analyze_transcript_chunk(session, transcript)
    except Exception as e:
        logger.error(f'Scene analysis failed: {e}')
        return jsonify({'error': 'Scene analysis failed'}), 500

    return jsonify({
        'scene_changed': result['scene_changed'],
        'scene_description': result['scene_description'],
        'image_url': result.get('image_url'),
        'scene': result.get('scene'),
        'transcript': transcript,
        'quality_score': session.quality_score or 0,
        'location_changed': result.get('location_changed', False),
        'location_label_short': result.get('location_label_short'),
        'location': result.get('location'),
    }), 200


@sessions_bp.route('/audio-chunk', methods=['POST'])
@token_required
def process_audio_chunk():
    """Receive a recorded audio chunk (multipart), transcribe with Whisper,
    then hand off to the same scene-analysis flow as /chunk."""
    user_id = g.current_user.get('user_id')

    session_token = request.form.get('session_token')
    if not session_token:
        return jsonify({'error': 'session_token required'}), 400

    audio_file = request.files.get('audio')
    if audio_file is None:
        return jsonify({'error': 'audio file required'}), 400

    session, error = SessionService.get_session_for_user(user_id, session_token)
    if error:
        return jsonify({'error': error}), 404

    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({'error': 'empty audio file'}), 400

    try:
        transcript = transcribe_audio(
            audio_bytes, filename=audio_file.filename or 'chunk.webm'
        )
    except Exception as e:
        logger.error(f'Whisper transcription failed: {e}')
        return jsonify({'error': 'Transcription failed'}), 500

    # Whisper returned nothing audible. Don't skip Claude entirely —
    # analyze_transcript_chunk decides whether to force a new image based
    # on session age / last-scene age, and we'd lose that signal if we
    # returned early. Pass a silence marker so Claude has SOMETHING to
    # react to (the prompt + force-new directive tell it to invent
    # atmosphere consistent with CURRENT LOCATION when the audio is sparse).
    if not transcript:
        from app.services.scene_service import _get_last_scene
        last = _get_last_scene(session.id)
        # Only call Claude if we'd actually force a scene; otherwise it's
        # wasted spend on a silent chunk that wouldn't generate anything.
        from datetime import datetime as _dt
        from app.services.scene_service import FORCE_NEW_SCENE_AFTER_SECONDS
        would_force = False
        if last is not None:
            if (_dt.utcnow() - last.created_at).total_seconds() >= FORCE_NEW_SCENE_AFTER_SECONDS:
                would_force = True
        elif session.started_at is not None:
            if (_dt.utcnow() - session.started_at).total_seconds() >= 90:
                would_force = True

        if not would_force:
            return jsonify({
                'scene_changed': False,
                'scene_description': None,
                'image_url': None,
                'transcript': '',
                'silent': True,
            }), 200

        transcript = '[silence at the table — quiet beats, no narration this chunk]'

    return _analyze_and_respond(session, transcript)


@sessions_bp.route('/chunk', methods=['POST'])
@token_required
def process_chunk():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token') or not data.get('transcript'):
        return jsonify({'error': 'session_token and transcript required'}), 400

    session, error = SessionService.get_session_for_user(
        user_id, data['session_token']
    )
    if error:
        return jsonify({'error': error}), 404

    if session.status != 'active':
        return jsonify({
            'error': f'Session is not active (current status: {session.status})'
        }), 400

    # Check chunk-level rate limits before scene analysis
    limit_result = RateLimiterService.check_chunk_limits(session)
    if limit_result:
        if limit_result.get('force_paused'):
            return jsonify(limit_result), 200
        # For cooldown: still run analysis but skip image generation
        try:
            result = analyze_transcript_chunk(
                session, data['transcript'], skip_image=True
            )
        except Exception as e:
            logger.error(f'Scene analysis failed: {e}')
            return jsonify({'error': 'Scene analysis failed'}), 500

        response = {
            'scene_changed': result['scene_changed'],
            'scene_description': result['scene_description'],
            'image_url': None,
        }
        response.update(limit_result)
        return jsonify(response), 200

    try:
        result = analyze_transcript_chunk(session, data['transcript'])
    except Exception as e:
        logger.error(f'Scene analysis failed: {e}')
        return jsonify({'error': 'Scene analysis failed'}), 500

    return jsonify({
        'scene_changed': result['scene_changed'],
        'scene_description': result['scene_description'],
        'image_url': result.get('image_url'),
        'scene': result.get('scene'),
        'location_changed': result.get('location_changed', False),
        'location_label_short': result.get('location_label_short'),
        'location': result.get('location'),
    }), 200


@sessions_bp.route('/current', methods=['GET'])
@token_required
def current_session():
    user_id = g.current_user.get('user_id')
    session = SessionService.get_active_session(user_id)
    if not session:
        return jsonify({'error': 'No active session'}), 404

    # Include the existing scenes so the Session page's feed re-populates
    # on refresh / restart, instead of showing an empty grid mid-session.
    scenes = (
        Scene.query
        .filter_by(session_id=session.id)
        .order_by(Scene.created_at.desc())
        .all()
    )
    payload = session.to_dict()
    payload['scenes'] = [s.to_dict() for s in scenes]
    return jsonify(payload), 200


@sessions_bp.route('/scenes/<int:scene_id>/thumbs-up', methods=['POST'])
@token_required
def thumbs_up_scene(scene_id):
    """DM gives this scene the explicit nod. -15 quality_score on first
    toggle (idempotent — repeated calls don't grind score down)."""
    user_id = g.current_user.get('user_id')
    scene = Scene.query.get(scene_id)
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404
    from app.models.session import Session as SessionModel
    sess = SessionModel.query.get(scene.session_id)
    if not sess or sess.user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    if scene.thumbs_up:
        # Already thumbs-up'd — no-op.
        return jsonify({'thumbs_up': True, 'quality_score': sess.quality_score or 0}), 200

    scene.thumbs_up = True
    sess.quality_score = (sess.quality_score or 0) - 15
    db.session.commit()
    return jsonify({'thumbs_up': True, 'quality_score': sess.quality_score}), 200


@sessions_bp.route('/scenes/<int:scene_id>', methods=['DELETE'])
@token_required
def delete_scene(scene_id):
    """Remove a bad scene from the feed. DM-only (the scene's session must
    belong to the caller). Also bumps image_count down so the per-session
    cap reflects only kept images."""
    user_id = g.current_user.get('user_id')

    scene = Scene.query.get(scene_id)
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404

    # Must own the session this scene lives on.
    from app.models.session import Session as SessionModel
    sess = SessionModel.query.get(scene.session_id)
    if not sess or sess.user_id != user_id:
        return jsonify({'error': 'Forbidden'}), 403

    db.session.delete(scene)
    if sess.image_count and sess.image_count > 0:
        sess.image_count -= 1
    db.session.commit()
    return jsonify({'deleted': True, 'scene_id': scene_id,
                    'image_count': sess.image_count}), 200


@sessions_bp.route('/latest-scene', methods=['GET'])
@token_required
def latest_scene():
    user_id = g.current_user.get('user_id')
    scene, error = SessionService.get_latest_scene(user_id)
    if error:
        return jsonify({'error': error}), 404

    # Resolve the active session + linked table once; we need it whether or
    # not a scene exists (for the opening title card and the show_captions
    # toggle).
    from app.models.game_table import GameTable
    from app.models.player_character import PlayerCharacter
    session = SessionService.get_active_session(user_id)

    show_captions = True
    show_daub_updates = True
    daub_state = 'gathering'
    if session and session.generation_started_at is not None:
        # If the fal call has been in flight for a reasonable window, mark
        # Daub as painting. Stale flag (>60s) means a crash happened —
        # treat as gathering rather than lie.
        from datetime import datetime as _dt
        age = (_dt.utcnow() - session.generation_started_at).total_seconds()
        if 0 <= age <= 60:
            daub_state = 'painting'
    title_card = None
    if session:
        table = GameTable.query.get(session.table_id) if session.table_id else None
        if table is not None:
            if table.show_captions is not None:
                show_captions = bool(table.show_captions)
            if table.show_daub_updates is not None:
                show_daub_updates = bool(table.show_daub_updates)

        characters = []
        if session.table_id:
            characters = [
                {'name': c.name, 'description': c.description}
                for c in PlayerCharacter.query.filter_by(table_id=session.table_id).all()
            ]

        title_card = {
            'table_name': table.name if table else None,
            'game_type': session.game_type,
            'art_style': session.art_style,
            'rating': session.rating,
            'characters': characters,
            'image_url': session.title_card_image_url,
            'scryer_name': (table.scryer_name if table else None) or 'Daub',
        }

    if not scene:
        return jsonify({
            'image_url': None,
            'show_captions': show_captions,
            'show_daub_updates': show_daub_updates,
            'daub_state': daub_state,
            'title_card': title_card,
        }), 200

    return jsonify({
        'image_url': scene.image_url,
        'image_path': scene.image_path,
        'scene_description': scene.scene_description,
        'caption': scene.caption,
        'show_captions': show_captions,
        'show_daub_updates': show_daub_updates,
        'daub_state': daub_state,
        'title_card': title_card,
        'created_at': scene.created_at.isoformat() if scene.created_at else None,
    }), 200


# ---------- DM Correction routes ----------

def _get_corrections_list(session_id: int) -> list[dict]:
    """Return all corrections for a session as a list of dicts."""
    corrections = (
        SessionCorrection.query
        .filter_by(session_id=session_id)
        .order_by(SessionCorrection.created_at.asc())
        .all()
    )
    return [c.to_dict() for c in corrections]


@sessions_bp.route('/correction', methods=['POST'])
@token_required
def create_correction():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token') or not data.get('text'):
        return jsonify({'error': 'session_token and text required'}), 400

    text = data['text'].strip()
    if not text or len(text) > 500:
        return jsonify({'error': 'text must be 1-500 characters'}), 400

    session, error = SessionService.get_session_for_user(
        user_id, data['session_token']
    )
    if error:
        return jsonify({'error': error}), 404

    correction = SessionCorrection(session_id=session.id, text=text)
    db.session.add(correction)
    # Quality signal: DM had to step in. +20 (worst — explicit "you got it wrong").
    session.quality_score = (session.quality_score or 0) + 20
    db.session.commit()

    return jsonify({
        'correction': correction.to_dict(),
        'corrections': _get_corrections_list(session.id),
    }), 201


@sessions_bp.route('/corrections', methods=['GET'])
@token_required
def list_corrections():
    user_id = g.current_user.get('user_id')
    session_token = request.args.get('session_token')
    if not session_token:
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.get_session_for_user(user_id, session_token)
    if error:
        return jsonify({'error': error}), 404

    return jsonify({'corrections': _get_corrections_list(session.id)}), 200


@sessions_bp.route('/correction/<int:correction_id>', methods=['DELETE'])
@token_required
def delete_correction(correction_id):
    user_id = g.current_user.get('user_id')

    correction = SessionCorrection.query.get(correction_id)
    if not correction:
        return jsonify({'error': 'Correction not found'}), 404

    # Verify the correction belongs to a session owned by this user
    session = correction.session
    if session.user_id != user_id:
        return jsonify({'error': 'Correction not found'}), 404

    session_id = correction.session_id
    db.session.delete(correction)
    db.session.commit()

    return jsonify({'corrections': _get_corrections_list(session_id)}), 200


@sessions_bp.route('/corrections/clear', methods=['POST'])
@token_required
def clear_corrections():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token'):
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.get_session_for_user(
        user_id, data['session_token']
    )
    if error:
        return jsonify({'error': error}), 404

    SessionCorrection.query.filter_by(session_id=session.id).delete()
    db.session.commit()

    return jsonify({'corrections': []}), 200


# ---------------------------------------------------------------------------
# Image regen routes
# ---------------------------------------------------------------------------
REGEN_LIMIT = 10


@sessions_bp.route('/change-image', methods=['POST'])
@token_required
def change_image():
    """DM-initiated 'give me a fresh take' on the current scene. Distinct
    from regen — no implication the previous image was wrong. Consumes an
    image budget (image_count++) and does NOT touch quality_score. 30s
    cooldown so it can't be spam-mashed."""
    user_id = g.current_user.get('user_id')
    data = request.get_json() or {}
    session_token = data.get('session_token')
    if not session_token:
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.get_session_for_user(user_id, session_token)
    if error:
        return jsonify({'error': error}), 404
    if session.status != 'active':
        return jsonify({
            'error': f'Session is not active (current status: {session.status})'
        }), 400

    # 30s cooldown
    from datetime import datetime as _dt, timedelta
    if session.last_change_image_at:
        elapsed = (_dt.utcnow() - session.last_change_image_at).total_seconds()
        if elapsed < 30:
            return jsonify({
                'error': 'cooldown',
                'cooldown_remaining_s': int(30 - elapsed),
            }), 429

    # Prefer the rolling transcript buffer over the last scene's chunk —
    # this gives Claude the FRESH narration since the last image, not
    # the stale audio that triggered the previous scene.
    base_transcript = (session.transcript_buffer or '').strip()
    if not base_transcript:
        latest_scene = (
            Scene.query.filter_by(session_id=session.id)
            .order_by(Scene.created_at.desc()).first()
        )
        base_transcript = (latest_scene.transcript_chunk if latest_scene else '') or ''
    guidance = (data.get('guidance') or '').strip()

    # Reuse the regen path semantics (skip evidence check + location guard,
    # don't bump quality_score) but with a friendlier directive — the DM
    # isn't saying the previous image was wrong, just wants a new view.
    directive = (
        'CHANGE_IMAGE: The DM asked for a fresh take on the current scene. '
        'NOT a correction — the previous image was fine; the table just '
        'wants a new view of the same moment / place. Return '
        'scene_changed=true with a new image_prompt + caption. Same '
        'CURRENT LOCATION unless the DM\'s guidance explicitly moves it. '
        'WHEN IN DOUBT, KEEP IT VAGUE — lean atmospheric.'
    )
    if guidance:
        directive += f'\n\nDM guidance for this take: {guidance}'

    transcript_input = (
        directive + '\n\n--- ORIGINAL TRANSCRIPT ---\n' + base_transcript
    )

    try:
        result = analyze_transcript_chunk(session, transcript_input, is_regen=True)
    except Exception as e:
        logger.error(f'Change-image scene analysis failed: {e}')
        return jsonify({'error': 'Image generation failed'}), 500

    session.last_change_image_at = _dt.utcnow()
    db.session.commit()

    return jsonify({
        'image_url': result.get('image_url'),
        'scene_description': result.get('scene_description'),
        'scene': result.get('scene'),
    }), 200


@sessions_bp.route('/regen', methods=['POST'])
@token_required
def regen_image():
    user_id = g.current_user.get('user_id')
    data = request.get_json()
    if not data or not data.get('session_token'):
        return jsonify({'error': 'session_token required'}), 400

    session, error = SessionService.get_session_for_user(
        user_id, data['session_token']
    )
    if error:
        return jsonify({'error': error}), 404

    if session.status != 'active':
        return jsonify({
            'error': f'Session is not active (current status: {session.status})'
        }), 400

    # Regen limit check
    limit = REGEN_LIMIT
    current_count = session.regen_count or 0

    if current_count >= limit:
        return jsonify({
            'remaining': 0,
            'limit': limit,
            'message': 'Regen limit reached',
        }), 429

    # Get the most recent scene for this session
    latest_scene = Scene.query.filter_by(
        session_id=session.id
    ).order_by(Scene.created_at.desc()).first()

    if not latest_scene:
        return jsonify({'error': 'No scene to regenerate'}), 400

    # Regen flow: re-run Claude with the latest transcript + ALL DM
    # corrections (which the system prompt already promotes as ground
    # truth) so the corrections actually take effect. The previous code
    # path resubmitted the cached image_prompt to fal verbatim, which is
    # why thumbs-down + correction produced an identical scene.
    guidance = (data.get('guidance') or '').strip()
    # Prefer the rolling buffer over the last scene's chunk so regen
    # reflects FRESH narration since the rejected image, not the audio
    # that produced it.
    transcript_for_regen = (session.transcript_buffer or '').strip()
    if not transcript_for_regen:
        transcript_for_regen = (latest_scene.transcript_chunk or '').strip()

    # Regen directive — tell Claude the DM rejected the previous render and
    # to re-interpret with fresh eyes, honoring DM CORRECTIONS literally.
    regen_directive = (
        'REGEN: DM rejected the previous image (was: '
        f'"{latest_scene.scene_description or "?"}"). Re-read the transcript '
        'and DM CORRECTIONS in the system prompt; honor every correction '
        'literally. Return scene_changed=true with a new scene_description, '
        'image_prompt, and caption that match.'
    )
    if guidance:
        regen_directive += f'\n\nExtra guidance for this attempt: {guidance}'

    transcript_input = (
        regen_directive + '\n\n--- ORIGINAL TRANSCRIPT ---\n' +
        transcript_for_regen
    )

    try:
        result = analyze_transcript_chunk(session, transcript_input, is_regen=True)
    except Exception as e:
        logger.error(f'Regen scene analysis failed: {e}')
        return jsonify({'error': 'Image generation failed'}), 500

    # Increment regen counter + quality signal (+10 — DM rejected the image).
    session.regen_count = current_count + 1
    session.quality_score = (session.quality_score or 0) + 10
    db.session.commit()

    remaining = limit - session.regen_count
    scene_obj = result.get('scene')

    return jsonify({
        'image_url': result.get('image_url'),
        'scene_description': result.get('scene_description'),
        'scene': scene_obj,
        'remaining_regens': remaining,
        'regen_count': session.regen_count,
    }), 200


@sessions_bp.route('/regen-info', methods=['GET'])
@token_required
def regen_info():
    user_id = g.current_user.get('user_id')

    session_token = request.args.get('session_token')
    if not session_token:
        return jsonify({'error': 'session_token query param required'}), 400

    session, error = SessionService.get_session_for_user(
        user_id, session_token
    )
    if error:
        return jsonify({'error': error}), 404

    limit = REGEN_LIMIT
    current_count = session.regen_count or 0

    return jsonify({
        'regen_count': current_count,
        'regen_limit': limit,
        'remaining': max(0, limit - current_count),
    }), 200
