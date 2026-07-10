# ==============================================================================
# File:      api/app/services/image_gen.py
# Purpose:   Image generation service. Generates scene images via fal.ai
#            (Flux Schnell) with a local Pillow-based dev fallback. Downloads
#            the result, applies a watermark, saves locally, and creates the
#            Scene record + updates session counters.
# Callers:   services/scene_service.py
# Callees:   models/session.py, models/scene.py, SQLAlchemy (db), requests,
#            Pillow, os, time
# Modified:  2026-06-01
# ==============================================================================
from app import db
from app.models.scene import Scene
from app.models.session import Session
from PIL import Image, ImageDraw, ImageFont
import requests as http_requests
import os
import time
import io
import logging
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config from env
# ---------------------------------------------------------------------------
IMAGE_GEN_API_KEY = os.getenv('IMAGE_GEN_API_KEY', '')
IMAGE_GEN_PROVIDER = os.getenv('IMAGE_GEN_PROVIDER', 'fal')
UPLOADS_DIR = os.getenv('UPLOADS_DIR', os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads'
))

# Cost estimate: ~0.5 cents per Flux Schnell generation
COST_PER_IMAGE_CENTS = 1  # round up to 1 cent to be safe


def _ensure_uploads_dir():
    os.makedirs(UPLOADS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Dev fallback: generate a colored placeholder with prompt text
# ---------------------------------------------------------------------------
def _generate_placeholder(prompt: str) -> tuple[str, str]:
    """Return (image_url, local_path) for a locally-generated placeholder."""
    _ensure_uploads_dir()

    img = Image.new('RGB', (768, 512), color=(40, 40, 60))
    draw = ImageDraw.Draw(img)

    # Wrap prompt text onto the image
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    except (IOError, OSError):
        font = ImageFont.load_default()

    # Simple word-wrap
    words = prompt.split()
    lines, current_line = [], ''
    for word in words:
        test = f'{current_line} {word}'.strip()
        if len(test) > 60:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test
    if current_line:
        lines.append(current_line)

    y = 30
    for line in lines[:20]:  # cap at 20 lines
        draw.text((20, y), line, fill=(200, 200, 220), font=font)
        y += 22

    # "DEV PLACEHOLDER" stamp
    draw.text((20, 460), "DEV PLACEHOLDER", fill=(255, 80, 80), font=font)

    filename = f'placeholder_{uuid.uuid4().hex[:12]}.png'
    local_path = os.path.join(UPLOADS_DIR, filename)
    img.save(local_path, 'PNG')

    # In dev mode there is no remote URL; use a local path-based URL
    image_url = f'/uploads/{filename}'
    return image_url, local_path


# ---------------------------------------------------------------------------
# Style enforcement
# ---------------------------------------------------------------------------
# Claude's image_prompt occasionally underweights or drops the art_style,
# letting Flux drift to photorealism or a mixed look across a session. We
# anchor the style server-side: lead the prompt with a strong descriptor
# (and an anti-style nudge for the most drift-prone choices) so the chosen
# style is consistent regardless of how Claude phrased the prompt.
# Important: NO ARTIST NAMES anywhere. Recraft V3 is text-aware and renders
# artist names as literal typography on the canvas ("FRANK FRAZETTA" typeset
# across the sky). Describe the aesthetic via concrete descriptors only.
STYLE_PRESETS = {
    'Oil Painting':   'classical oil painting on canvas, rich textured brushwork, museum quality, NOT photorealistic, NOT photograph',
    'Watercolor':     'soft watercolor painting, visible paper texture, loose washes of color, painterly bleeding edges, NOT photorealistic, NOT 3d render',
    'Comic Book':     'comic book illustration, bold black ink outlines, flat saturated colors, halftone shading, sharp panel art style, NOT photorealistic, NOT photograph, NOT 3d render',
    'Pencil Sketch':  'graphite pencil sketch, hand-drawn linework, cross-hatching, monochrome shading, sketchbook paper texture, NOT photorealistic, NOT color photo',
    'Digital Art':    'modern digital fantasy illustration, polished and crisp, vivid colors, painterly digital aesthetic',
}

# Per-style negative additions appended to image_prompt. Tightens the
# anti-drift rule for each style's most common Recraft/Flux failure mode.
STYLE_NEGATIVES = {
    'Oil Painting':   'no photograph, no digital art, no contemporary attire',
    'Watercolor':     'no contemporary clothing, no modern fashion, no neon',
    'Comic Book':     'no photograph, no realistic faces, no CGI',
    'Pencil Sketch':  'no color photography, no digital effects',
    'Digital Art':    'no photograph, no realistic faces',
}

# Universal anti-text suffix appended to EVERY prompt. Recraft V3 will
# happily typeset words from the prompt as literal canvas text — artist
# names, style descriptors, even adjective fragments. This suffix
# pre-empts that failure mode regardless of model.
NO_TEXT_SUFFIX = (
    'no text, no typography, no lettering, no watermark, no artist '
    'signature, no caption, no title card, no written words on the image'
)


# Legacy style-name mapping. Older sessions/tables may still have these
# values in art_style; map them to safe modern equivalents so we never
# (a) miss the STYLE_PRESETS lookup and fall through to "in the style of
# Frazetta", which would put the artist's name in the prompt and risk
# both the typeset bug and the IP concern, or (b) leak a deprecated style
# label into a generated prompt.
LEGACY_STYLE_MAP = {
    'Frazetta':   'Oil Painting',
    'frazetta':   'Oil Painting',
    'Retro AD&D': 'Oil Painting',
    'retro_add':  'Oil Painting',
    'AD&D':       'Oil Painting',
}


def _normalize_style(art_style: str | None) -> str | None:
    """Translate legacy style values to their current equivalents.
    Returns the input unchanged if it's already a valid current style or
    None."""
    if not art_style:
        return art_style
    return LEGACY_STYLE_MAP.get(art_style, art_style)


def _apply_style(prompt: str, art_style: str | None) -> str:
    """Lead the prompt with a style anchor. Falls back to a generic
    'painterly fantasy illustration' lead-in for any unknown style —
    NEVER echoes the raw art_style value into the prompt (avoids leaking
    artist names or stale labels)."""
    art_style = _normalize_style(art_style)
    if not art_style:
        return prompt
    anchor = STYLE_PRESETS.get(
        art_style,
        'painterly fantasy illustration, rich atmospheric brushwork, '
        'NOT photorealistic, NOT photograph'
    )
    return f'{anchor}. {prompt}'


def _apply_no_party_guard(prompt: str, session: Session) -> str:
    """Hard server-side anti-people rule.

    Always appended (regardless of whether the table has described
    characters): no unnamed humans in the frame. Flux/dev tends to crowd
    scenes with generic townsfolk, modern-looking faces, and background
    figures even when the prompt doesn't ask for them. This suffix steers
    it toward landscapes, architecture, and atmosphere.

    Justified people (party members with descriptions, recurring NPCs,
    transcript-named-and-described characters) are still allowed because
    Claude's image_prompt has already named them explicitly — fal weights
    explicit subjects above generic suppressions."""
    return (
        prompt +
        ', wide establishing shot, environment-focused composition, '
        'cinematic background painting, NO unnamed people in foreground, '
        'NO unnamed people in midground, NO foreground crowds, '
        'NO midground crowds, NO townsfolk in the front of frame, '
        'NO modern clothing, NO contemporary attire, NO photorealistic '
        'faces, NO close-up portrait framing'
    )


# ---------------------------------------------------------------------------
# fal.ai Flux Schnell via REST API
# ---------------------------------------------------------------------------
def _generate_fal(prompt: str, image_model: str | None = None) -> tuple[str, bytes]:
    """Call fal.ai image gen. Returns (remote_url, image_bytes).

    image_model is the fal model slug (e.g. "fal-ai/recraft-v3",
    "fal-ai/flux/dev"). Falls back to env IMAGE_MODEL_DEFAULT then
    recraft-v3. Recraft endpoint gets a `style` parameter; flux variants
    don't accept it. Other models pass just the basic payload.
    """
    model = image_model or os.getenv('IMAGE_MODEL_DEFAULT', 'fal-ai/recraft-v3')
    url = f'https://queue.fal.run/{model}'
    headers = {
        'Authorization': f'Key {IMAGE_GEN_API_KEY}',
        'Content-Type': 'application/json',
    }

    # Universal anti-text suffix. Always appended so Recraft/Flux can't
    # decide to typeset words from the prompt onto the canvas. Cheap
    # insurance — adds ~150 chars to every prompt.
    safe_prompt = f'{prompt}. {NO_TEXT_SUFFIX}'

    # Recraft V3 enforces a ~1000-char prompt limit and 422s anything
    # over it. Truncate defensively (try to cut on a sentence boundary).
    # We add the NO_TEXT_SUFFIX BEFORE truncation so it's the last thing
    # to get cut — but reserve room for it via the cutoff math below.
    if 'recraft' in model and len(safe_prompt) > 950:
        # Reserve room for the suffix at the end; cut the main prompt
        # and re-append the suffix so anti-text rules survive truncation.
        suffix_with_period = f'. {NO_TEXT_SUFFIX}'
        budget = 950 - len(suffix_with_period)
        cutoff = prompt.rfind('. ', 0, budget)
        if cutoff < 400:
            cutoff = budget
        safe_prompt = prompt[:cutoff].rstrip().rstrip('.') + suffix_with_period

    payload: dict = {
        'prompt': safe_prompt,
        'image_size': 'landscape_16_9',
    }
    if 'recraft' in model:
        # Recraft V3 wants style + (optional) colors + num_images. Some
        # parameters that work for flux trip 422 here, so keep payload
        # tight.
        payload['style'] = 'digital_illustration'
        payload['colors'] = []
    payload.setdefault('num_images', 1)

    # Submit the request
    resp = http_requests.post(url, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    result = resp.json()

    # fal queue API: if we get a request_id, poll for completion using the
    # status_url / response_url returned by the submit call (constructing them
    # manually returns 405 on the current fal API).
    if 'request_id' in result and 'images' not in result:
        status_url = result.get('status_url')
        result_url = result.get('response_url')
        if not status_url or not result_url:
            raise RuntimeError(
                f'fal.ai submit response missing status_url/response_url: {result}'
            )

        # Poll for up to 120 seconds
        for _ in range(60):
            time.sleep(2)
            status_resp = http_requests.get(status_url, headers=headers, timeout=30)
            status_resp.raise_for_status()
            status_data = status_resp.json()
            if status_data.get('status') == 'COMPLETED':
                break
        else:
            raise TimeoutError('fal.ai image generation timed out after 120s')

        # Fetch result
        result_resp = http_requests.get(result_url, headers=headers, timeout=30)
        result_resp.raise_for_status()
        result = result_resp.json()

    images = result.get('images', [])
    if not images:
        raise RuntimeError('fal.ai returned no images')

    remote_url = images[0]['url']
    img_resp = http_requests.get(remote_url, timeout=60)
    img_resp.raise_for_status()

    return remote_url, img_resp.content


# ---------------------------------------------------------------------------
# Watermark
# ---------------------------------------------------------------------------
def _apply_watermark(image_bytes: bytes) -> Image.Image:
    """Add semi-transparent 'townscryer.gg' watermark in the bottom-right."""
    img = Image.open(io.BytesIO(image_bytes)).convert('RGBA')

    # Create watermark overlay
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    except (IOError, OSError):
        font = ImageFont.load_default()

    text = 'townscryer.gg'
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    x = img.width - text_w - 15
    y = img.height - text_h - 15

    # Semi-transparent white text with dark shadow
    draw.text((x + 1, y + 1), text, fill=(0, 0, 0, 100), font=font)
    draw.text((x, y), text, fill=(255, 255, 255, 140), font=font)

    return Image.alpha_composite(img, overlay).convert('RGB')


# ---------------------------------------------------------------------------
# Score-gated visual audit (Claude vision)
# ---------------------------------------------------------------------------
# When session.quality_score >= AUDIT_QUALITY_THRESHOLD (= the DM is
# correcting / regenning a lot), we send the rendered image back to Claude
# with a quick "did Flux blow it" audit. If the audit spots an issue
# (snow when corrections say no snow, telephone poles, modern attire,
# wrong character), we tweak the prompt and re-fal ONCE. Cost is gated:
# only struggling sessions pay for this; clean runs skip the audit
# entirely.
AUDIT_QUALITY_THRESHOLD = int(os.getenv('AUDIT_QUALITY_THRESHOLD', '30'))

# Hard duplicate-shot check. Gated hybrid: cheap server-side bookkeeping
# (subject_category from Claude's scene response) decides whether to fire
# an expensive Claude-vision compare. When subject_category repeats in
# the last 2 scenes, we ask Claude vision to look at prev+new and judge
# duplicate. If yes, regen ONCE with a Claude-supplied fresh concept.
# Capped at MAX_DUPE_RETRIES_PER_SESSION so a stubborn Recraft attractor
# can't drain the budget.
DUPLICATE_CHECK_ENABLED = os.getenv('DUPLICATE_CHECK_ENABLED', '1') == '1'
MAX_DUPE_RETRIES_PER_SESSION = int(os.getenv('MAX_DUPE_RETRIES_PER_SESSION', '3'))


def _audit_image(session, image_url: str, image_prompt: str) -> dict:
    """Ask Claude (vision) whether the rendered image matches the prompt
    and respects the active DM corrections. Returns a dict with `pass`
    (bool), `issues` (list[str]), and `retry_addition` (str)."""
    from app.models.session_correction import SessionCorrection
    import anthropic
    import json as _json

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        return {'pass': True, 'issues': [], 'retry_addition': ''}

    corrections = (
        SessionCorrection.query
        .filter_by(session_id=session.id)
        .order_by(SessionCorrection.created_at.asc())
        .all()
    )
    corrections_summary = '; '.join(c.text for c in corrections) if corrections else '(none)'

    audit_prompt = (
        'You painted this image. Time for a tight audit before we show '
        'it to the table.\n\n'
        f'IMAGE_PROMPT YOU SENT TO FLUX: "{image_prompt}"\n\n'
        f'DM CORRECTIONS FOR THIS CAMPAIGN: {corrections_summary}\n\n'
        'AUDIT METHOD: Scan the image and answer EACH of the following '
        'questions Y/N. Anything Y is a fail.\n\n'
        'KNOWN-FAILURE CHECKLIST (always-on, applies regardless of '
        'corrections):\n'
        '  Q1. Is there any visible TEXT, typography, lettering, '
        'watermark, artist signature, or written words on the canvas? '
        '(e.g. "FRANK FRAZETTA" typeset across the sky.)\n'
        '  Q2. Are there telephone poles, power lines, electric '
        'infrastructure, paved asphalt roads, modern signage, fence '
        'posts with wire?\n'
        '  Q3. Is anyone in the image wearing modern attire — jeans, '
        't-shirts, hoodies, sneakers, sunglasses, contemporary 21st-'
        'century clothing?\n'
        '  Q4. Are there any photorealistic human faces, photographic '
        'skin/eye detail, or CGI 3D-rendered character models — when '
        'the IMAGE_PROMPT specifies a painted/illustrated style?\n'
        '  Q5. Does the rendered art style clearly NOT match the style '
        'words in the IMAGE_PROMPT (e.g. prompt says "watercolor", '
        'image is a photograph)?\n'
        '  Q6. Are there generic background crowds, townsfolk, '
        'passersby, or unnamed figures that the IMAGE_PROMPT did NOT '
        'explicitly request?\n\n'
        'CORRECTION CHECKLIST (only applies when corrections exist):\n'
        '  Q7. Is any element flagged in the DM CORRECTIONS as '
        'NEVER-INCLUDE visible in the image? (e.g. "no snow" → check '
        'for snow; "no telephone poles" → check for poles.)\n'
        '  Q8. SCENE-SPECIFIC corrections ("show the campsite", "the '
        'wagon should be broken") — only apply when the IMAGE_PROMPT '
        'itself describes that element. Do NOT flag a missing campsite '
        'when the prompt is about a wide road shot.\n\n'
        'IMPORTANT EXCLUSIONS:\n'
        '  - Do NOT enforce continuity with previous scenes.\n'
        '  - Do NOT flag a missing element from a prior scene if the '
        'current prompt doesn\'t describe it.\n\n'
        'Respond JSON only. Schema:\n'
        '{"pass": true|false, "issues": ["Q1: yes, FRANK FRAZETTA '
        'typeset upper sky", "Q3: yes, figure wearing jeans"], '
        '"retry_addition": "additional positive language to add to the '
        'prompt to fix the issues — be specific. For Q1 add \'no text, '
        'no typography, no watermark\'. For Q2 add \'no telephone poles, '
        'no power lines, no modern infrastructure\'. For Q3 add \'all '
        'figures in period-appropriate medieval attire\'."}'
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        model_id = session.scene_model or os.getenv(
            'SCENE_MODEL_DEFAULT', 'claude-haiku-4-5-20251001'
        )
        # Claude vision accepts image URLs directly.
        message = client.messages.create(
            model=model_id,
            max_tokens=512,
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'image', 'source': {'type': 'url', 'url': image_url}},
                    {'type': 'text', 'text': audit_prompt},
                ],
            }],
        )
        raw = message.content[0].text.strip()
        if raw.startswith('```'):
            lines = [l for l in raw.split('\n') if not l.strip().startswith('```')]
            raw = '\n'.join(lines).strip()
        return _json.loads(raw)
    except Exception:
        logger.exception('Visual audit failed; treating as pass')
        return {'pass': True, 'issues': [], 'retry_addition': ''}


def _check_duplicate_shot(session, prev_image_url: str, new_image_url: str,
                          new_image_prompt: str) -> dict:
    """Hard duplicate check. Send prev+new images to Claude vision and ask
    "is this essentially the same shot?" If yes, Claude returns a fresh
    image_prompt that breaks the pattern. Otherwise returns is_duplicate
    false. Returns dict with keys: is_duplicate (bool), similarity_notes
    (str), new_image_prompt (str)."""
    from app.models.session_correction import SessionCorrection
    import anthropic
    import json as _json

    api_key = os.getenv('ANTHROPIC_API_KEY', '')
    if not api_key:
        return {'is_duplicate': False}

    corrections = (
        SessionCorrection.query
        .filter_by(session_id=session.id)
        .order_by(SessionCorrection.created_at.asc())
        .all()
    )
    corrections_summary = (
        '; '.join(c.text for c in corrections) if corrections else '(none)'
    )

    style_anchor = STYLE_PRESETS.get(session.art_style or '', '')

    instructions = (
        'Hard duplicate-shot check. You painted BOTH of these images for '
        'the same campaign. Compare with a tight eye — is the SECOND '
        'image essentially the SAME SHOT as the FIRST?\n\n'
        f'CURRENT IMAGE_PROMPT YOU SENT: "{new_image_prompt[:500]}"\n'
        f'STYLE: {session.art_style}\n'
        f'DM CORRECTIONS: {corrections_summary}\n\n'
        'DUPLICATE = same lead subject in same composition, regardless of '
        'relighting or minor prop changes. "Broken wagon on a winding '
        'road through grass" vs "Broken wagon on a winding road through '
        'grass with different sky" = DUPLICATE. NOT a duplicate: a '
        'close-up of the wagon wheel vs a wide of the wagon; a '
        'character\'s face vs the same location\'s wagon; a different '
        'lead focal subject entirely.\n\n'
        'If DUPLICATE: write a NEW image_prompt that breaks the pattern. '
        'Same location is fine; same SHOT is not. Pick a different lead '
        'focal subject (a character\'s face, hands at work, an object, a '
        'piece of architecture, the weather itself, a detail in the '
        'scene). Push any recurring props OUT of the lead position. Do '
        'NOT change time of day or weather. Lead the new prompt with '
        f'this style anchor verbatim: "{style_anchor}"\n\n'
        'Respond JSON only. Schema:\n'
        '{"is_duplicate": true|false, "similarity_notes": "what '
        'specifically is similar", "new_image_prompt": "full replacement '
        'prompt if duplicate, empty string otherwise"}'
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        model_id = session.scene_model or os.getenv(
            'SCENE_MODEL_DEFAULT', 'claude-haiku-4-5-20251001'
        )
        message = client.messages.create(
            model=model_id,
            max_tokens=1024,
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': 'FIRST IMAGE (previous scene):'},
                    {'type': 'image', 'source': {'type': 'url', 'url': prev_image_url}},
                    {'type': 'text', 'text': 'SECOND IMAGE (just generated):'},
                    {'type': 'image', 'source': {'type': 'url', 'url': new_image_url}},
                    {'type': 'text', 'text': instructions},
                ],
            }],
        )
        raw = message.content[0].text.strip()
        if raw.startswith('```'):
            lines = [l for l in raw.split('\n') if not l.strip().startswith('```')]
            raw = '\n'.join(lines).strip()
        return _json.loads(raw)
    except Exception:
        logger.exception('Duplicate-shot check failed; treating as not duplicate')
        return {'is_duplicate': False}


# ---------------------------------------------------------------------------
# Title-card poster generation (one-shot at session start)
# ---------------------------------------------------------------------------
def generate_title_card(session: Session, table_name: str | None) -> str | None:
    """Generate a movie-poster style backdrop for the session's title card.
    Stored on session.title_card_image_url and shown on the Display behind
    the campaign name + tags + party listing. No Scene record is created
    (this is chrome, not a scene). Returns the URL or None on failure."""
    if not IMAGE_GEN_API_KEY:
        return None

    # CRITICAL: do NOT pass the table name into the prompt. Recraft is
    # text-aware and will TYPESET the name onto the canvas — usually
    # garbled (we saw "CRITICAL RATISY" / "NAL ADTMELIEL SAMDILER"
    # for table name "Critical Roll"). The Display already overlays the
    # campaign name in clean web typography; the AI image is JUST the
    # backdrop. Avoid the words "title", "card", and "text" entirely in
    # the positive frame so Recraft has no conceptual anchor for
    # rendering type.
    poster_prompt = (
        f'A cinematic establishing landscape for a {session.game_type} '
        'adventure. Wide atmospheric vista, evocative mood, sweeping '
        'view, hero-shot composition with large open sky and a clean '
        'spacious foreground. Empty frame — no people, no signage, no '
        'symbols, no markings, no banners. Just landscape, weather, '
        'light, atmosphere.'
    )
    final_prompt = _apply_style(poster_prompt, session.art_style)

    try:
        remote_url, _img_bytes = _generate_fal(final_prompt, getattr(session, 'image_model', None))
        return remote_url
    except Exception:
        logger.exception('Title card generation failed')
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_image(
    session: Session,
    prompt: str,
    scene_description: str,
    transcript_chunk: str,
    caption: str | None = None,
    location: str | None = None,
    subject_category: str | None = None,
    location_label_short: str | None = None,
) -> dict:
    """Generate an image, watermark it, save locally, create Scene record.

    Returns dict with keys: image_url, image_path, scene_description,
    generation_time_ms.
    """
    start_ms = int(time.time() * 1000)

    # Mark the session as actively painting so the Display's polling can
    # show "Daub the Painter is painting…" while fal is in flight.
    from datetime import datetime as _dt
    session.generation_started_at = _dt.utcnow()
    db.session.commit()

    # Single-source-of-truth principle: Claude writes the entire prompt
    # Flux sees. The style anchor, no-people rule, anti-Flux-drift
    # positives, and DM-correction substitutions are all baked into
    # Claude's image_prompt via the system prompt. No server-side
    # appending — Flux is a fresh stateless world every call, and
    # layering server-side cues only fights with Claude's intent.
    final_prompt = prompt

    if not IMAGE_GEN_API_KEY:
        # Dev fallback
        logger.info('IMAGE_GEN_API_KEY not set; using placeholder generator')
        image_url, local_path = _generate_placeholder(final_prompt)
    else:
        # Production: call fal.ai
        remote_url, image_bytes = _generate_fal(final_prompt, getattr(session, 'image_model', None))
        image_url = remote_url

        # Hard duplicate-shot check. Always-on (configurable via env)
        # but cheap-gated: only fires the expensive Claude-vision call
        # when subject_category repeats in the last 2 scenes. Capped at
        # MAX_DUPE_RETRIES_PER_SESSION so a stubborn Recraft attractor
        # can't drain the budget.
        if (
            DUPLICATE_CHECK_ENABLED
            and subject_category
            and (session.dupe_retry_count or 0) < MAX_DUPE_RETRIES_PER_SESSION
        ):
            # Look at the last 2 scenes' subject categories. If the new
            # category matches either, we have a potential rut — call
            # vision to confirm or deny.
            recent = (
                Scene.query
                .filter_by(session_id=session.id)
                .order_by(Scene.created_at.desc())
                .limit(2)
                .all()
            )
            recent_categories = [
                (s.subject_category or '').strip().lower()
                for s in recent if s.subject_category
            ]
            current_cat = subject_category.strip().lower()
            category_repeats = current_cat and current_cat in recent_categories

            if category_repeats and recent and recent[0].image_url:
                session.dupe_check_count = (session.dupe_check_count or 0) + 1
                db.session.commit()
                logger.info(
                    f'Subject category "{current_cat}" repeats for '
                    f'session {session.id}; running vision dupe check'
                )
                dupe = _check_duplicate_shot(
                    session, recent[0].image_url, remote_url, final_prompt
                )
                if dupe.get('is_duplicate'):
                    new_prompt = (dupe.get('new_image_prompt') or '').strip()
                    notes = dupe.get('similarity_notes', '')
                    if new_prompt:
                        logger.info(
                            f'Duplicate shot CONFIRMED for session '
                            f'{session.id}. Notes: {notes!r}. Regen with '
                            f'fresh concept (retry '
                            f'{(session.dupe_retry_count or 0) + 1}/'
                            f'{MAX_DUPE_RETRIES_PER_SESSION}).'
                        )
                        try:
                            remote_url, image_bytes = _generate_fal(
                                new_prompt,
                                getattr(session, 'image_model', None),
                            )
                            image_url = remote_url
                            final_prompt = new_prompt
                            session.dupe_retry_count = (
                                session.dupe_retry_count or 0
                            ) + 1
                            db.session.commit()
                        except Exception:
                            logger.exception(
                                'Dupe-retry fal call failed; keeping original'
                            )
                else:
                    logger.info(
                        f'Vision dupe check PASSED for session {session.id} '
                        f'(category "{current_cat}" repeats but images '
                        f'compose differently)'
                    )

        # Score-gated visual audit. Only runs when the session has been
        # struggling (quality_score >= AUDIT_QUALITY_THRESHOLD). Cheap
        # runs skip the cost. Max one retry per scene.
        if (session.quality_score or 0) >= AUDIT_QUALITY_THRESHOLD:
            session.audit_count = (session.audit_count or 0) + 1
            db.session.commit()
            audit = _audit_image(session, remote_url, final_prompt)
            if not audit.get('pass', True):
                addition = (audit.get('retry_addition') or '').strip()
                issues = audit.get('issues', [])
                logger.info(
                    f'Visual audit failed for session {session.id} — '
                    f'issues: {issues}. Retrying with addition: {addition!r}'
                )
                retry_prompt = (
                    final_prompt + (', ' + addition if addition else '')
                )
                try:
                    remote_url, image_bytes = _generate_fal(
                        retry_prompt,
                        getattr(session, 'image_model', None),
                    )
                    image_url = remote_url
                    final_prompt = retry_prompt
                    session.audit_retry_count = (session.audit_retry_count or 0) + 1
                    db.session.commit()
                except Exception:
                    logger.exception('Audit retry fal call failed; keeping original image')

        # Watermark and save locally
        _ensure_uploads_dir()
        watermarked = _apply_watermark(image_bytes)
        filename = f'scene_{uuid.uuid4().hex[:12]}.png'
        local_path = os.path.join(UPLOADS_DIR, filename)
        watermarked.save(local_path, 'PNG')

    elapsed_ms = int(time.time() * 1000) - start_ms

    # Create Scene record (store the FINAL prompt that actually went to fal,
    # not Claude's raw image_prompt, so debugging and regen match what was
    # rendered).
    scene = Scene(
        session_id=session.id,
        image_url=image_url,
        image_path=local_path,
        prompt=final_prompt,
        scene_description=scene_description,
        caption=caption,
        location=location,
        transcript_chunk=transcript_chunk,
        generation_time_ms=elapsed_ms,
        subject_category=subject_category,
        location_label_short=location_label_short,
    )
    db.session.add(scene)

    # Update session counters. Quality signal lives upstream in
    # scene_service so it can distinguish a natural scene from a regen.
    session.image_count = (session.image_count or 0) + 1
    session.estimated_cost_cents = (session.estimated_cost_cents or 0) + COST_PER_IMAGE_CENTS
    # Clear the in-flight marker so Daub's status flips back to "gathering".
    session.generation_started_at = None

    db.session.commit()

    # Increment user's monthly image counter
    from app.services.rate_limiter_service import RateLimiterService
    RateLimiterService.increment_monthly_image_count(session.user_id)

    return {
        'image_url': image_url,
        'image_path': local_path,
        'scene_description': scene_description,
        'generation_time_ms': elapsed_ms,
        'scene': scene.to_dict(),
    }
