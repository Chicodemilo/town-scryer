# ==============================================================================
# File:      api/app/services/scene_service.py
# Purpose:   Scene extraction service. Sends transcript chunks to Claude Haiku
#            to detect scene changes, then triggers image generation when the
#            physical environment shifts.
# Callers:   routes/sessions.py
# Callees:   services/image_gen.py, models/scene.py, models/session.py,
#            anthropic, SQLAlchemy (db), json, os, logging
# Modified:  2026-06-01
# ==============================================================================
from app import db
from app.models.scene import Scene
from app.models.session import Session
from datetime import datetime
from app.models.player_character import PlayerCharacter
from app.models.npc import Npc
from app.models.game_table import GameTable
from app.models.session_correction import SessionCorrection
from app.services.image_gen import (
    generate_image, STYLE_PRESETS, STYLE_NEGATIVES, _normalize_style,
)
import anthropic
import json
import os
import re
import logging

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
# Default model when the session has no scene_model snapshot. Per-session
# resolution is preferred; this is only the floor.
DEFAULT_SCENE_MODEL = os.getenv(
    'SCENE_MODEL_DEFAULT', 'claude-haiku-4-5-20251001'
)

# Panel cadence floor. The display refreshes at least every 120 seconds —
# this is the PRIMARY trigger, not a fallback. Claude's job on each chunk
# is to flag DRAMATIC MOMENTS that warrant beating this cadence (an early
# interrupt), not to decide every routine scene change. Inverted hybrid:
# cadence-default + listening-as-interrupt.
FORCE_NEW_SCENE_AFTER_SECONDS = 120


# High-confidence scene-change phrases. The server scans each incoming
# chunk's transcript for these; if any match, we prepend a STRONG HINT
# directive to Claude's user_content so it doesn't sleep on the cue.
# These are intentionally narrow — match phrases a DM uses to BEGIN a
# new visual beat, not generic verbs.
_STRONG_HINTS = (
    # Soft + hard entries
    'you arrive at', 'you reach the', 'you reach a', 'you enter the',
    'you enter a', 'you step into', 'you step through', 'you cross the',
    'you head into', 'you walk into', 'you ride into', 'you fly into',
    'you drop into', 'you climb into', 'you crest the',
    'arrives at the', 'reaches the gate', 'comes upon a', 'comes upon the',
    'find yourselves in', 'finds himself in', 'finds herself in',
    "you're standing in", "you're standing at", "you're at the",
    # Environmental transformation
    'the corridor opens', 'the trees thin', 'the trees clear',
    'opens into a', 'opens into the', 'the fog lifts', 'the mist lifts',
    'dawn breaks', 'dusk falls', 'nightfall', 'night falls',
    'the rain stops', 'the rain begins', 'the storm rolls',
    # Combat / drama
    'rolls initiative', 'roll initiative', 'draws his sword',
    'draws her sword', 'draws their sword', 'draws his weapon',
    'draws her weapon', 'draws their weapon', 'drew his',
    'casts fireball', 'casts polymorph', 'casts time stop',
    'magic missile', 'channel divinity', 'wild shape',
    'drops to the', 'falls to the', 'crashes into',
    'is dead', 'goes down', 'go down', 'unconscious',
    'the dragon', 'the lich', 'the doors open', 'the door opens',
)


def _find_strong_hint(transcript: str) -> str | None:
    """Return the first matched strong-hint phrase, or None. Used to
    prepend a STRONG HINT directive that pushes Claude to fire."""
    if not transcript:
        return None
    lower = transcript.lower()
    for phrase in _STRONG_HINTS:
        if phrase in lower:
            return phrase
    return None


# Movement signals — used to RECOGNIZE clearly-justified location changes
# (party explicitly moves). Kept around as a positive signal, no longer as
# a default-block gate.
_MOVEMENT_SIGNALS = (
    'head ', 'heads ', 'headed ', 'heading ',
    'walk', 'ran ', 'run ', 'running ',
    'arrive', 'enter', 'step ', 'stepped ', 'stepping ',
    'travel', 'journey', 'approach', 'reach ', 'reached ', 'reaching ',
    'leave ', 'left ', 'leaves ', 'depart',
    'ride ', 'rode ', 'flies', 'flew', 'flying',
    'teleport', 'portal',
    'find yourselves', 'find ourselves', 'finds yourself',
    'wake ', 'wakes ', 'waking', 'awake',
    'into the ', 'into a ', 'into an ',
    'onto the ', 'onto a ', 'onto an ',
    'open the door', 'opens the door', 'open the gate',
    'cross the', 'crossed the',
    "you're in ", "you are in ", "you're at ", "you are at ",
    "you're standing", "you stand",
    'thins', 'clears', 'lifts', 'rolls in',
    'breaks open', 'opens into',
)


def _transcript_has_movement(transcript: str) -> bool:
    """True if the transcript contains a movement or environmental-
    transition signal that justifies a location change."""
    if not transcript:
        return False
    lower = transcript.lower()
    return any(sig in lower for sig in _MOVEMENT_SIGNALS)


# Hallucination patterns: known cases where Claude's training prior fires
# a location change purely from an activity verb. "drinking" → tavern,
# "eating" → inn, "sleeping" → bedroom. We block ONLY these specific
# transitions when there's no movement signal — everything else passes.
# (Default-allow with a targeted block list, inverted from the previous
# default-block model.)
_HALLUCINATION_PATTERNS = {
    'drink':  ('tavern', 'pub', 'bar', 'saloon'),
    'drank':  ('tavern', 'pub', 'bar', 'saloon'),
    'eat':    ('inn', 'restaurant', 'dining hall', 'kitchen'),
    'eating': ('inn', 'restaurant', 'dining hall', 'kitchen'),
    'sleep':  ('bedroom', 'inn', 'bed', 'bunk'),
    'rest':   ('bedroom', 'inn', 'campsite'),
    'shop':   ('market', 'shop', 'store', 'bazaar', 'stall'),
    'pray':   ('temple', 'shrine', 'altar', 'church'),
}


def _is_hallucinated_location_change(transcript: str, new_location: str) -> bool:
    """Block only known activity→place hallucinations when no movement
    signal is present. Everything else is allowed through.

    Returns True if the change matches a hallucination pattern AND no
    movement signal exists.
    """
    if not transcript or not new_location:
        return False
    if _transcript_has_movement(transcript):
        return False  # Movement signal → trust the change
    transcript_lower = transcript.lower()
    new_lower = new_location.lower()
    for activity_root, place_signals in _HALLUCINATION_PATTERNS.items():
        if activity_root in transcript_lower and any(
            p in new_lower for p in place_signals
        ):
            return True
    return False


def _build_system_prompt(
    session: Session,
    last_scene_description: str | None,
    image_count: int = 0,
    current_location: str | None = None,
    suppress_last_scene: bool = False,
) -> str:
    """Build the system prompt for Claude with session context.

    Ordering matters: OVERRIDES (DM corrections) come first, then GROUND
    TRUTH (location, notes, party, npcs, last scene), then the RULES for
    triggering and composing images, then edge cases, then the JSON schema.
    """
    parts: list[str] = []

    # Resolve style anchor that Claude must lead its image_prompt with.
    # Normalize legacy art_style values (e.g. "Frazetta" → "Oil Painting")
    # before lookup so we never echo a deprecated label or artist name into
    # the prompt. Unknown styles fall back to a neutral painterly anchor.
    style_key = _normalize_style(session.art_style or '') or ''
    style_label = style_key or session.art_style or 'painterly'
    style_anchor = STYLE_PRESETS.get(
        style_key,
        'painterly fantasy illustration, rich atmospheric brushwork, '
        'NOT photorealistic, NOT photograph'
    )

    # ----- Identity + session config -----
    scryer_name = 'Daub'
    if session.table_id:
        _t = GameTable.query.get(session.table_id)
        if _t and _t.scryer_name:
            scryer_name = _t.scryer_name
    parts.append(
        f'You are {scryer_name}, also called "{scryer_name} the Painter" '
        f'or just "the Painter" — the visual oracle for a live tabletop '
        f'RPG session. You listen to the table and paint the scene on the '
        f'players\' screen. Game: {session.game_type}. Art style: '
        f'{style_label}. Rating: {session.rating}. Images produced '
        f'so far: {image_count}.'
    )
    parts.append(
        f'WAKE WORD — When a transcript line addresses you as '
        f'"{scryer_name}", "{scryer_name} the Painter", or "the Painter" '
        f'(e.g. "{scryer_name}, switch to the inn", "Painter, show us the '
        f'dragon", "{scryer_name} the Painter, that\'s a forest not a '
        f'tavern"), treat EVERYTHING that follows the address on that '
        f'line as a DIRECT DM COMMAND, ranked above passive interpretation '
        f'of the transcript and above the previous scene. These directives '
        f'function exactly like a DM Correction — honor literally on the '
        f'next image.'
    )

    # ----- OVERRIDES — DM corrections (highest priority; placed FIRST) -----
    corrections = (
        SessionCorrection.query
        .filter_by(session_id=session.id)
        .order_by(SessionCorrection.created_at.asc())
        .all()
    )
    if corrections:
        parts.append('')
        parts.append(
            'DM CORRECTIONS — override EVERYTHING below. The DM is in the '
            'room and sees the real game; trust them over your own '
            'inference, the transcript, or the previous scene. Honor each '
            'one literally on the next image:'
        )
        for c in corrections:
            parts.append(f'- {c.text}')

    # ----- GROUND TRUTH -----
    parts.append('')
    if current_location:
        parts.append(
            f'CURRENT LOCATION: {current_location}. Sticky — keep it until '
            'the transcript explicitly describes movement OR the place '
            'itself transforms (see triggers below).'
        )
    if suppress_last_scene:
        # On force/regen we deliberately OMIT "Last scene shown" so Claude
        # doesn't receive conflicting signals — the subject-swap block in
        # the user message already carries the previous-scene context with
        # the correct "diverge from this" framing. Two echoes of the past
        # subtly nudge Claude back to the same composition.
        parts.append(
            "You're being asked to paint a DIFFERENT shot than the "
            "previous scene. See the SUBJECT SWAP REQUIRED block in the "
            "user message — that's the binding directive."
        )
    elif last_scene_description:
        parts.append(f'Last scene shown: {last_scene_description}')
    else:
        parts.append('No scene has been shown yet.')

    # ----- Party / NPCs / Notes -----
    if session.table_id:
        characters = PlayerCharacter.query.filter_by(
            table_id=session.table_id
        ).all()
        renderable = [c for c in characters if (c.description or '').strip()]
        anonymous = [c for c in characters if not (c.description or '').strip()]

        if renderable:
            parts.append('')
            parts.append('Party members you may render (match descriptions):')
            for i, pc in enumerate(renderable, 1):
                parts.append(f'{i}. {pc.name} — {pc.description}')
        if anonymous:
            parts.append('')
            parts.append(
                'Party members with NO description — DO NOT RENDER them. No '
                'silhouettes, no backs, no shadow figures. Omit from the '
                'image entirely; caption may still name them: '
                + ', '.join(c.name for c in anonymous)
            )
        if not characters:
            parts.append('')
            parts.append(
                'No party entered. DO NOT render party members in any form. '
                'Images are about place + action + named NPCs/enemies only.'
            )

        npcs = Npc.query.filter_by(table_id=session.table_id).all()
        if npcs:
            parts.append('')
            parts.append(
                'Recurring NPCs (keep visually consistent when they appear):'
            )
            for i, n in enumerate(npcs, 1):
                desc = n.description or '(no description)'
                parts.append(f'{i}. {n.name} — {desc}')

        table = GameTable.query.get(session.table_id)
        if table and table.notes:
            parts.append('')
            parts.append('DM notes (world / lore, treat as ground truth):')
            parts.append(table.notes)

    # ----- TRIGGER RULES — inverted hybrid -----
    parts.extend([
        '',
        'PANEL CADENCE — the system fires a panel refresh every 120 '
        'seconds automatically as a safety net. The cadence catches '
        'routine atmospheric refreshes (same place, mood drift) so you '
        'don\'t have to. But you ARE listening, and when the narration '
        'genuinely changes the picture, you fire it. Don\'t wait for '
        'cadence on real signals.',
        '',
        'YOUR JOB ON EACH CHUNK — fire scene_changed=true when:',
        '',
        '  • LOCATION CHANGE — the party moves to a meaningfully '
        'different place. SOFT entries qualify: "you arrive at the '
        'village", "you reach the crossroads", "you step into the inn", '
        '"you crest the hill and see…". HARD entries qualify: "we step '
        'through the portal", "we drop into the lair". If the visual '
        'character of the place SHIFTS, fire — do NOT wait for cadence.',
        '  • ENVIRONMENTAL TRANSFORMATION — same place, but the '
        'visuals shift. "The fog lifts", "dawn breaks", "the corridor '
        'opens into a vast chamber", "the rain stops", "the trees thin '
        'into meadow". These are panel-worthy.',
        '  • COMBAT START — the party crosses from talk/explore into '
        'a fight. Swords drawn, initiative rolled, first hit lands.',
        '  • DEATH or NEAR-DEATH — a character drops, a killing blow '
        'lands, someone is bleeding out.',
        '  • BIG SPELL — fireball, polymorph, summon, time-stop, plane-'
        'shift, revivify. The kind of spell that gets a panel in a comic.',
        '  • BOSS REVEAL — the dragon arrives, the lich speaks, the '
        'veil drops, the BBEG enters the room.',
        '  • TWIST / BETRAYAL — the NPC turns, the artifact was a '
        'fake, the trusted ally is the villain.',
        '  • RESURRECTION / ASCENSION — return from the dead, a '
        'transformation, a level-up cinematic.',
        '  • DM CORRECTION — the DM has just typed a correction or '
        'said the wake word; honor it immediately.',
        '',
        'DO NOT FIRE for:',
        '  • Routine activity inside a stable place — drinking, '
        'planning, chatting, dice rolls, arguing.',
        '  • RECAP audio — past-tense narration about events already '
        'past ("last we left off…", "previously the party…", "when '
        'we last saw you…", "upon this conflict you decided…"). '
        'Recap is for the listeners, not the canvas. Return '
        'scene_changed=false and let the title card hold. If the DM '
        'pivots from recap into present-tense action ("NOW you find '
        'yourselves…", "OKAY, you wake up to…"), THEN fire the '
        'establishing shot on the pivot — not on the recap that '
        'preceded it.',
        '  • Idle chatter, in-jokes, "did anyone bring beer".',
        '',
        'WHEN IN DOUBT on a real signal — FIRE IT. Better an extra '
        'panel than a missed location change. The cadence is the safety '
        'net under you, not the primary trigger.',
        '',
        'ACTIVITY ≠ LOCATION. When you DO call a location change, make '
        'sure it\'s an actual location change, not an activity. Drinking '
        'whiskey does NOT mean a tavern. Eating does NOT mean an inn. '
        'Sleeping does NOT mean a bedroom. Activity says what they are '
        'doing; location only changes on explicit movement OR clear '
        'environmental transformation.',
    ])

    # ----- FLUX-FACING IMAGE_PROMPT REQUIREMENTS -----
    parts.extend([
        '',
        'IMAGE_PROMPT IS A FRESH WORLD EVERY TIME. The image_prompt you '
        'return is sent VERBATIM to a stateless image generator (Flux). '
        'Flux has NO memory of previous chunks, NO awareness of corrections, '
        'NO awareness of this system prompt, NO knowledge of the party, '
        'NO knowledge of CURRENT LOCATION or DM corrections — only the '
        'text you write in image_prompt. The image_prompt must be 100% '
        'self-contained. Bake everything Flux needs into it:',
        '',
        f'  • LEAD with the style anchor (use exactly this text at the '
        f'start of image_prompt): "{style_anchor}"' if style_anchor else
        '  • LEAD with the chosen art style as the first words of image_prompt.',
        '  • Then a wide-shot framing cue ("wide establishing shot, '
        'cinematic background painting").',
        '  • Then the scene/place description — positively descriptive, '
        'concrete environmental language Flux can paint (textures, '
        'materials, light direction, color palette).',
        '  • DM corrections are NOT visible to Flux. Translate each active '
        'correction into a POSITIVE substitution in the image_prompt. '
        'Negation does not work on Flux ("no snow" often produces snow). '
        'Instead, describe what IS there: a "no snow" correction becomes '
        '"dry brown earth, bare ground, autumn dead grass, no '
        'precipitation, clear hard-packed road". A "no modern '
        'infrastructure" correction becomes "pre-industrial medieval '
        'fantasy setting, only natural shoulders on the path, stone '
        'milestones, no man-made vertical structures on the verge".',
        '  • If no described characters justify a person in frame, end '
        'the image_prompt with: "no unnamed people in foreground, no '
        'unnamed people in midground, no crowds in foreground or '
        'midground, no modern attire, no contemporary clothing, no '
        'photorealistic faces, no close-up portrait framing".',
        '',
        'KNOWN FLUX DRIFT MODES — bake counters into image_prompt when '
        'relevant:',
        '  • "cold/winter/frost" → Flux adds SNOW. Counter: "dry brown '
        'earth, bare ground, late autumn dead grass, no snow, no winter '
        'precipitation".',
        '  • "country road / rural / wilderness" → Flux adds TELEPHONE '
        'POLES. Counter: "pre-industrial medieval fantasy, no telephone '
        'poles, no power lines, no wooden poles, no modern signage, only '
        'natural roadside".',
        '  • "tavern / market / village" → Flux adds CROWDS in modern '
        'attire. Counter: bake quietness into the scene ("empty tavern '
        'common room", "deserted market at dawn") OR cite the verbatim '
        'evidence for a crowd and explicitly call it "distant medieval '
        'fantasy peasant figures, tiny silhouettes far in the deep '
        'background, no modern attire, no contemporary clothing".',
        '  • Generic "people gathering" → Flux defaults to MODERN faces '
        'and modern clothing. Counter: never leave "people" generic; '
        'either omit, or specify exactly which character (named, '
        'described) appears.',
        '',
        'WHEN IN DOUBT — KEEP IT VAGUE. SENSE THE ATMOSPHERE. If the '
        'transcript is sparse, silent, or ambiguous, do NOT invent '
        'specifics (a particular NPC face, exact furniture, a numbered '
        'group of guards). Lean atmospheric: weather, light, shadow, '
        'distance, time of day, color palette, sense of place. Wrong '
        'specifics break the room; mood holds the room. *"A dim corridor '
        'heavy with damp"* beats *"a stone corridor with three iron '
        'sconces and a red banner"* when you don\'t actually know what\'s '
        'there.',
        '',
        'NO INVENTED PROPS. The transcript names what is in the scene. '
        'Do NOT add objects, vehicles, structures, animals, or props the '
        'transcript did not explicitly mention. Specifically:',
        '  • Travel narration ("you head north", "the party rides toward '
        'the town") does NOT entitle you to a wagon, cart, horse, or '
        'mount unless one is named. The party may be on foot.',
        '  • Settlement narration ("you arrive at the inn") does NOT '
        'entitle you to invent specific furniture, signage, barrels, or '
        'NPCs. Paint the place\'s exterior or its empty interior.',
        '  • Camp narration ("you make camp", "you rest for the night") '
        'does NOT entitle you to invent a campfire, tents, bedrolls, or '
        'specific gear unless the DM says so. Paint terrain + weather + '
        'light.',
        '  • If the DM names a prop (wagon, banner, statue, sword on the '
        'altar), THEN it goes in the image. Otherwise — landscape, '
        'weather, architecture, atmosphere ONLY.',
        '',
        'NO FRANCHISE KNOWLEDGE / NO TRAINING DATA LEAKAGE — HARD '
        'RULE, ZERO TOLERANCE. The audio may sound like a famous '
        'campaign (Critical Role, Dimension 20, a specific module). '
        'DO NOT use franchise lore, canon, place names, or any general '
        'training knowledge to fill in scene details.\n'
        '  • PROPER NOUN TEST: when the transcript contains a proper '
        'noun you recognize from outside this session (Mighty Nein, '
        'Zadash, the Underworks, Strahd, Barovia, the Underdark, '
        'Berylbridge, Xhorhas, Aeor, Wildemount, Kring Dynasty, '
        'Yasha, Caduceus, etc.), DO NOT use the name itself in your '
        '`location`, `scene_description`, or `image_prompt` fields. '
        'You may pass the name through in `caption` if it adds '
        'narrative flavor, but NEVER let canon place-names appear in '
        'fields that drive the IMAGE.\n'
        '  • DO NOT invent visual details about a named place based on '
        'what you know — "Zadash" is just a string of letters to you. '
        'You have no idea what its walls look like, what its market '
        'sells, who its guards are. Treat it as if the DM made up the '
        'name on the spot.\n'
        '  • If the transcript only names a place without describing '
        'its appearance, describe the GENERIC archetype based on '
        'context ("a fortified medieval city gate") and let the '
        'transcript do the rest. Do NOT paint specifics.\n'
        '  • Specifically: no Critical Role wagons, no Mighty Nein '
        'character likenesses, no campaign-canon NPCs, no canon-'
        'specific architecture. Treat every session as a private game '
        'you have NO outside knowledge of.',
        '',
        'FRAMING DEFAULT — ZOOM OUT. You are painting BACKGROUNDS, not '
        'portraits. Default to wide-angle, establishing-shot composition: '
        'the whole tavern, not a face at the bar; the forest valley, not a '
        'leaf; the dragon\'s lair from across the chamber, not the '
        'dragon\'s eye. Closeups are reserved for the rare dramatic '
        'moment when the panel demands one (a deathblow, a reveal). '
        'Otherwise the camera sits back and shows the world.',
        '',
        'IMAGE COMPOSITION — every image_prompt is built in this order:',
        '',
        '  (0) DEFAULT = NO PEOPLE. Start every image_prompt as if the '
        'frame is empty of humans. The default subject is the world: '
        'place, architecture, landscape, weather, light, objects.',
        '    A FOREGROUND or MIDGROUND person is added ONLY when one of '
        'these is true — no others:',
        '      (a) Listed above in PARTY MEMBERS WITH KNOWN APPEARANCES.',
        '      (b) Listed above in RECURRING NPCs.',
        '      (c) Named AND described in THIS transcript chunk (e.g. '
        '"the innkeeper Helga, a stout halfling with flour on her apron" '
        '— qualifies).',
        '    Otherwise NO patrons, NO "a figure stands", NO "a guard '
        'approaches", NO silhouettes. Empty rooms / streets / roads are '
        'fine.',
        '    DISTANT BACKGROUND CROWDS — narrowly allowed only when the '
        'transcript provides direct evidence of a crowd ("the market is '
        'packed", "villagers gather outside"). Cite the phrase in '
        'scene_change_evidence. Render as tiny silhouettes deep in the '
        'frame. Never invent a crowd from genre habit.',
        '',
        '  (1) Scene / background = the subject. Lead with setting, time of '
        'day, weather, lighting, architecture, terrain.',
        '  (2) Action / mood = inside that place. Embers drifting, swords '
        'mid-swing, whiskey bottles around the campfire (without hands '
        'attached unless those hands belong to a justified person from '
        'rule 0). Action shapes mood; it does not replace the place.',
        '  (3) Characters = only those that passed rule 0. Match their '
        'descriptions exactly. A character-less image of the right place '
        'beats a character-full image of the wrong place.',
    ])

    # ----- EDGE CASES -----
    if image_count == 0:
        parts.extend([
            '',
            'FIRST IMAGE — be PATIENT. The title card is already on screen '
            'and a "Daub is listening… gathering information" pulse is '
            'reassuring the table that you\'re here. So you do NOT need to '
            'fire fast — you need to fire RIGHT.',
            '',
            'Decision tree for chunk 1+:',
            '  - Is this clearly the game starting? (DM voice of authority: '
            '"Okay, last time we were…", "When we left off…", "You find '
            'yourselves…", "Today we begin…", "The party arrives at…" — '
            'often a recap followed by a present-tense pivot to "NOW '
            'you\'re standing at…"). If YES → fire a wide ESTABLISHING '
            'shot of the place the DM names. No characters in foreground '
            '— setting + atmosphere + mood, splash-page style.',
            '  - Is this clearly pre-game (greetings, snacks, in-jokes, '
            'rules talk, last week\'s recap, "did anyone bring beer")? '
            'If YES → return scene_changed=false. Hold on the title card. '
            'Patience wins; the title card has a backdrop and a listening '
            'pulse for exactly this moment.',
            '  - Is it AMBIGUOUS (the DM is recapping but might pivot any '
            'second, the table is half-narrating, you can\'t tell)? '
            'Return scene_changed=false. Wait one more chunk. Better to '
            'hold the title card for an extra 30-60 seconds than fire a '
            'wrong first image that defines the night.',
            '  - Is the transcript empty or silent? Default = hold off, '
            'BUT the system will auto-force a first scene at 90 seconds of '
            'session uptime regardless; you don\'t need to fire blind.',
            '',
            'The bar for firing the FIRST image is higher than any later '
            'image. You can be wrong on image 5 (just regen). You really '
            'cannot afford to be wrong on image 1.',
        ])
    elif image_count <= 3:
        parts.append('')
        parts.append(
            f'OPENING SHOTS ({image_count}/3 done). Keep images establishing '
            '— wide, atmospheric, the world settling in. No combat closeups '
            'or dramatic panel shots yet; save those for image 4+.'
        )

    parts.extend([
        '',
        'OFF-TOPIC AUDIO. If the transcript is clearly not TTRPG (a work '
        'meeting, phone call, music, kids arguing), reimagine it in-genre '
        'instead of refusing: a standup becomes a council of mages, a '
        'phone argument becomes feuding dragons, a baby crying becomes a '
        'demon waking. Trigger a scene change and let it paint over the '
        'previous one. Caption may wink at the absurdity; image stays '
        'in-world.',
    ])

    # ----- OUTPUT SCHEMA -----
    parts.extend([
        '',
        'Respond with JSON only. Schema:',
        '{"scene_changed": boolean, "location_changed": boolean, '
        '"location": "short label for the current physical place. Echo the '
        'CURRENT LOCATION above verbatim if unchanged. NO franchise '
        'proper nouns (no \\"Zadash\\", no \\"the Underworks\\", etc).", '
        '"location_label_short": "REQUIRED. ALWAYS include this field. '
        'VERY short 3-5 word chyron-style tag for the location, '
        'evocative not literal. Examples: \\"Misty marsh dawn\\", '
        '\\"Stone corridor below\\", \\"Tavern, fire crackling\\", '
        '\\"Cliffside, wind howling\\", \\"Forest path, gold light\\". '
        'Used as a brief DM ping when location changes. NOT a sentence. '
        'NOT a full description. Just a few mood-loaded words. NO '
        'franchise proper nouns in this field.", '
        '"scene_change_evidence": "Quote from the transcript that justifies '
        'the early interrupt — paraphrasing is OK but at least one 3-word '
        'phrase in your quote MUST appear verbatim in the transcript below '
        '(server-side check will reject otherwise). Minimum 3 words total. '
        'Required when scene_changed=true. If you can\'t cite any phrase '
        'that survives that check, this isn\'t actually a dramatic moment — '
        'set scene_changed=false and let the cadence handle it.", '
        '"scene_description": "1-3 sentences describing the new scene", '
        '"image_prompt": "detailed prompt for the image generator, '
        'scene-first per the composition rules above", '
        '"subject_category": "short snake_case tag categorizing the '
        'IMAGE\'s lead subject. Examples: broken_wagon_landscape, '
        'character_face_closeup, interior_architecture, '
        'weather_phenomenon, object_detail, party_silhouette, '
        'monster_reveal, magical_effect, battlefield_aftermath, '
        'campfire_circle, road_through_terrain. Pick what fits; '
        'CONSISTENCY between similar shots matters more than exhaustive '
        'categorization — if you painted a broken_wagon_landscape last '
        'time and you\'re painting another broken wagon, USE THE SAME '
        'tag. The server uses this to detect repeated subjects.", '
        '"caption": "ONE short punchy line (<=60 chars, ideally 4-8 '
        'words), present-tense, evocative, no quotation marks — think a '
        'chyron"}',
    ])

    return '\n'.join(parts)


def _get_last_scene(session_id: int) -> Scene | None:
    """Return the most recent Scene for this session, or None."""
    return (
        Scene.query
        .filter_by(session_id=session_id)
        .order_by(Scene.created_at.desc())
        .first()
    )


def _get_last_scene_description(session_id: int) -> str | None:
    scene = _get_last_scene(session_id)
    return scene.scene_description if scene else None


def analyze_transcript_chunk(session: Session, transcript: str, skip_image: bool = False, is_regen: bool = False) -> dict:
    """Analyze a transcript chunk for scene changes.

    If skip_image is True, scene analysis still runs but image generation is
    skipped (used when rate-limit cooldown is active).

    Returns dict with keys: scene_changed, scene_description, image_url.
    """
    last_scene = _get_last_scene(session.id)
    last_description = last_scene.scene_description if last_scene else None
    last_location = last_scene.location if last_scene else None
    image_count = session.image_count or 0

    # Force-new-scene guard. Computed BEFORE building the system prompt so
    # we can suppress the "Last scene shown" line — on force/regen the
    # subject-swap block carries that context with the correct "diverge"
    # framing, and showing both at once gives Claude conflicting signals.
    # Fires when:
    #   - last image is older than FORCE_NEW_SCENE_AFTER_SECONDS, OR
    #   - the session has no image yet and has been running for at least
    #     90 seconds (so the screen doesn't stay on the title card forever
    #     because Claude keeps holding for the perfect game-start cue).
    force_new_scene = False
    if last_scene is not None:
        age = (datetime.utcnow() - last_scene.created_at).total_seconds()
        if age >= FORCE_NEW_SCENE_AFTER_SECONDS:
            force_new_scene = True
    elif session.started_at is not None:
        session_age = (datetime.utcnow() - session.started_at).total_seconds()
        if session_age >= 90:
            force_new_scene = True
            logger.info(
                f'Forcing first scene for session {session.id} — '
                f'session has been active for {int(session_age)}s with no '
                f'image yet'
            )

    system_prompt = _build_system_prompt(
        session, last_description, image_count,
        current_location=last_location,
        suppress_last_scene=(force_new_scene or is_regen),
    )

    # Subject-swap block for force/regen paths. When we refresh the canvas
    # without new transcript material (180s timeout, DM regen, DM Make A
    # New Image), Recraft will happily repaint the same composition relit
    # unless we explicitly push Claude OFF the previous subject. The
    # near-duplicate-shots failure mode comes from Recraft's composition
    # attractors locking in when the prompt shape doesn't change.
    previous_image_prompt = (last_scene.prompt if last_scene else '') or ''
    subject_swap_block = ''
    if (force_new_scene or is_regen) and previous_image_prompt:
        subject_swap_block = (
            '\n\n--- PREVIOUS IMAGE_PROMPT (do not repeat this composition) ---\n'
            f'"{previous_image_prompt[:600]}"\n\n'
            'SUBJECT SWAP REQUIRED. The previous image used the subject above. '
            'You MUST switch to a DIFFERENT focal subject:\n'
            '  - Pick a different focal element entirely — a character\'s '
            'face, hands at work, an object (a sword, a kettle, a map, a '
            'piece of armor, a wound), a piece of architecture, the '
            'weather itself, footprints, debris, an animal.\n'
            '  - Push recurring props (wagons, campfires, cottages, '
            'horses) OUT of frame or to the periphery — they MUST NOT be '
            'the lead subject. Same location is fine; same SHOT is not.\n'
            '  - Do NOT change time of day or weather — those break '
            'narrative continuity. Variation comes from subject, angle, '
            'and focal element, NOT from relighting.\n'
            '  - Lead image_prompt with the NEW focal subject as the '
            'first concrete noun after the style anchor.\n'
        )

    # Detect silent cadence-fire — when the audio side passes the synthetic
    # silence sentinel, the table is between beats and Claude has nothing
    # narrative to anchor on. Default cadence behavior would paint another
    # version of the same place and we'd rut. Switch to free-improv mode:
    # demand a fundamentally different composition, not a continuation.
    is_silent_force = (
        force_new_scene
        and isinstance(transcript, str)
        and transcript.startswith('[silence at the table')
    )

    # Prior-context block: feed Claude the recent transcript leading up
    # to this chunk so it can read the NARRATIVE ARC, not just the
    # current 15-30s in isolation. Lots of scene changes straddle chunk
    # boundaries ("you ride for three days" → next chunk → "and arrive
    # at the gates of Zadash") — without prior context Claude sees only
    # half the cue and holds. We use the rolling transcript_buffer which
    # excludes the current chunk (the buffer is appended AFTER the call).
    prior_block = ''
    buffer_text = (session.transcript_buffer or '').strip()
    if buffer_text and not is_regen:
        # Last ~2000 chars ≈ 90s of speech, enough to see the lead-up
        # without overwhelming the context window. Skip on regen — the
        # regen route shapes its own context.
        prior = buffer_text[-2000:]
        prior_block = (
            '\n\n--- PRIOR TRANSCRIPT (lead-up to current chunk, for '
            'context only) ---\n'
            + prior +
            '\n--- END PRIOR TRANSCRIPT ---\n\n'
        )

    # Strong-hint scanner: if the current chunk contains a high-confidence
    # scene-change phrase ("you arrive at", "rolls initiative", "the fog
    # lifts", etc.), prepend a STRONG HINT directive that pushes Claude
    # to fire. This is a server-side trip-wire on top of Claude's own
    # judgment — covers the cases where Sonnet's caution suppresses an
    # obvious cue.
    strong_hint = _find_strong_hint(transcript) if not is_regen else None
    hint_block = ''
    if strong_hint:
        hint_block = (
            f'\n\nSTRONG HINT — the server detected the phrase '
            f'"{strong_hint}" in this chunk. That phrase is on the list '
            'of high-confidence scene-change cues (LOCATION CHANGE, '
            'ENVIRONMENTAL TRANSFORMATION, COMBAT START, or DRAMATIC '
            'MOMENT). Strongly favor scene_changed=true on this chunk '
            'unless the phrase is clearly being used in past-tense '
            'recap or quoted out-of-character.\n'
        )

    user_content = prior_block + hint_block + transcript
    if is_silent_force:
        user_content = (
            f'SILENT CADENCE FIRE: {FORCE_NEW_SCENE_AFTER_SECONDS}s since '
            'last image AND the table is between beats — Whisper got '
            'silence on the last chunk. The DM is mid-thought, taking a '
            'sip, checking notes. There is NO new narration to react to.\n\n'
            'This is FREE-IMPROV MODE. Don\'t paint another version of '
            'the place you just painted — the screen wants freshness. '
            'Push hard for VARIETY:\n'
            '  • Pick a fundamentally different lead subject from the '
            'last 2 images. Avoid recurring props entirely.\n'
            '  • Try an EXTREME framing — way close (a detail: a rune, a '
            'tool, an insect, a hand, a wound) OR way wide (a god\'s-eye '
            'view of the region, the horizon from above).\n'
            '  • OR go pure mood — weather alone (rain on stone, mist on '
            'grass, sun cutting through cloud), sky alone, ground alone.\n'
            '  • OR an animal/creature in the scene\'s biome (a heron in '
            'the marsh, a fox crossing the path, ravens on a branch). '
            'Atmospheric, not narrative.\n'
            '  • OR a time-of-day pivot — dawn cracking, dusk falling, '
            'starlight breaking through cloud.\n'
            'Same CURRENT LOCATION is fine, but the SHOT should feel '
            'like a different panel of a comic, not a relight of the '
            'previous one. Subject_category should be from a different '
            'family than the last 2.'
            f'{subject_swap_block}'
            f'{prior_block}'
            '\n--- TRANSCRIPT (silent) ---\n' + transcript
        )
    elif force_new_scene:
        user_content = (
            f'CADENCE FIRE: {FORCE_NEW_SCENE_AFTER_SECONDS}s since last '
            'image. Time for the next panel. Return scene_changed=true '
            'with a fresh image_prompt + caption. This is a ROUTINE panel '
            'refresh, not a dramatic interrupt — lean atmospheric '
            '(light, weather, shadow, mood, distance) over invented '
            'specifics. Better a moody refresh of CURRENT LOCATION than a '
            'confident wrong detail.'
            f'{subject_swap_block}'
            f'{prior_block}'
            f'{hint_block}'
            '\n--- TRANSCRIPT ---\n' + transcript
        )
    elif is_regen and subject_swap_block:
        # Regen route shapes its own transcript context already; append
        # the subject-swap directive so Claude knows to diverge from the
        # previous image rather than rebuild it.
        user_content = transcript + subject_swap_block

    # Call Claude with whichever model the session was started under.
    # Falls back to env default, then hardcoded Haiku.
    model_id = session.scene_model or DEFAULT_SCENE_MODEL
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model_id,
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {'role': 'user', 'content': user_content},
        ],
    )

    # Increment API call counter + append this chunk to the rolling
    # transcript buffer so regen / Make-A-New-Image can grab fresh
    # context later. Skip on regens — they already include the buffered
    # transcript so re-appending it would amplify.
    session.api_call_count = (session.api_call_count or 0) + 1
    if not is_regen and transcript:
        existing = (session.transcript_buffer or '').strip()
        appended = (existing + ' ' + transcript).strip() if existing else transcript
        # Trim to last ~5000 chars to keep the column small.
        if len(appended) > 5000:
            appended = appended[-5000:]
        session.transcript_buffer = appended
    db.session.commit()

    # Parse the response
    raw_text = message.content[0].text.strip()

    # Handle possible markdown code fences
    if raw_text.startswith('```'):
        lines = raw_text.split('\n')
        # Remove first and last lines (the fences)
        lines = [l for l in lines if not l.strip().startswith('```')]
        raw_text = '\n'.join(lines).strip()

    result = None
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # Step 1: try to extract a JSON object from anywhere in the
        # response. Sonnet sometimes wraps the JSON in explanatory prose
        # ("Here is the analysis: {...}.") — the JSON is in there, just
        # not on its own.
        match = re.search(r'\{[\s\S]*\}', raw_text)
        if match:
            try:
                result = json.loads(match.group(0))
                logger.info(
                    f'Recovered JSON from prose-wrapped response for session '
                    f'{session.id}'
                )
            except json.JSONDecodeError:
                result = None

    if result is None:
        # Step 2: one retry with a stricter system message telling Claude
        # to return ONLY JSON. ~$0.001 extra per parse failure, recovers
        # most cases. Without this, the chunk would be silently lost.
        logger.warning(
            f'JSON parse failed for session {session.id}, retrying with '
            f'strict-JSON system: {raw_text[:200]!r}'
        )
        try:
            retry = client.messages.create(
                model=model_id,
                max_tokens=1024,
                system=(
                    system_prompt
                    + '\n\nIMPORTANT: Return ONLY the JSON object. No '
                    'prose, no explanation, no markdown fences. Start '
                    'with { and end with }.'
                ),
                messages=[{'role': 'user', 'content': user_content}],
            )
            retry_text = retry.content[0].text.strip()
            if retry_text.startswith('```'):
                retry_text = '\n'.join(
                    l for l in retry_text.split('\n')
                    if not l.strip().startswith('```')
                ).strip()
            result = json.loads(retry_text)
        except Exception:
            logger.exception(
                f'JSON retry also failed for session {session.id}; '
                f'falling back to no-change'
            )
            return {
                'scene_changed': False,
                'scene_description': last_description,
                'image_url': None,
            }

    scene_changed = result.get('scene_changed', False)
    scene_description = result.get('scene_description', '')
    image_prompt = result.get('image_prompt', '')
    caption = (result.get('caption') or '').strip()[:80] or None
    subject_category = (result.get('subject_category') or '').strip()[:80] or None
    location_label_short = (result.get('location_label_short') or '').strip()[:100] or None

    # Evidence check: a scene_changed=true claim must point at a phrase
    # that actually appears in the transcript. Catches the "Claude latched
    # onto a single noun and built a scene around it" failure mode.
    # Uses a 3-word n-gram match (not strict substring) because the LLM
    # often paraphrases or auto-corrects Whisper's transcription when
    # quoting, even though the DM did say roughly that thing. Skipped on
    # regens and forced scenes — those paths have their own justifications.
    if scene_changed and not force_new_scene and not is_regen:
        evidence = (result.get('scene_change_evidence') or '').strip()
        evidence_words = evidence.lower().split()
        transcript_lower = transcript.lower()

        # Build all 3-word phrases from the evidence, check if any survive
        # in the transcript verbatim.
        ngram_hit = False
        if len(evidence_words) >= 3:
            for i in range(len(evidence_words) - 2):
                phrase = ' '.join(evidence_words[i:i + 3])
                if phrase in transcript_lower:
                    ngram_hit = True
                    break

        if not evidence or len(evidence_words) < 3 or not ngram_hit:
            logger.warning(
                f'Blocked unjustified scene change — evidence failed check '
                f'(words={len(evidence_words)}, ngram_hit={ngram_hit}, '
                f'evidence={evidence!r}). Transcript: {transcript[:120]!r}'
            )
            scene_changed = False

    # Style guarantee — even though Claude is told to lead the
    # image_prompt with the style anchor, Sonnet sometimes paraphrases or
    # buries it mid-prompt. If the anchor isn't found verbatim at the
    # start, prepend it. Cheap insurance for visual consistency across
    # the session.
    if image_prompt:
        anchor = STYLE_PRESETS.get(_normalize_style(session.art_style) or '')
        if anchor and not image_prompt.lower().startswith(anchor.lower()[:25]):
            image_prompt = f'{anchor}. {image_prompt}'

    # Resolve location. Server-side enforcement of two rules Claude keeps
    # violating:
    #   (1) If location_changed=false, the location stays last_location.
    #       (Claude sometimes echoes a wrong "new" location while still
    #       claiming nothing changed — ignore the echo.)
    #   (2) If location_changed=true but the transcript has no movement
    #       signal, the change is unjustified — block it. Hold the previous
    #       location and skip image generation this round so the display
    #       doesn't show a wrong-place panel.
    raw_location = (result.get('location') or '').strip()[:150]
    location_changed_flag = bool(result.get('location_changed', False))

    if last_location and location_changed_flag and not is_regen and _is_hallucinated_location_change(transcript, raw_location):
        logger.warning(
            f'Blocked hallucinated location change: '
            f'"{last_location}" -> "{raw_location}" — matches a known '
            f'activity→place pattern with no movement signal. '
            f'Transcript: {transcript[:120]!r}'
        )
        location = last_location
        location_changed_flag = False
        scene_changed = False  # Skip image gen; keep the previous image up.
    elif location_changed_flag and raw_location:
        location = raw_location
    elif last_location:
        # Sticky: ignore any "echoed" new location when nothing changed.
        location = last_location
    else:
        # First scene of the session — accept whatever Claude returned.
        location = raw_location or None

    # Belt-and-suspenders: if we asked for a forced scene and Claude still
    # returned scene_changed=false (or no image_prompt), override.
    if force_new_scene:
        scene_changed = True
        if not image_prompt and scene_description:
            image_prompt = scene_description

    # Character description post-check. Claude is told to bake party
    # descriptions into image_prompt, but Sonnet sometimes names a
    # character without including their visual cues — leaving the image
    # generator to render a generic adventurer face. Belt-and-suspenders:
    # if a named character appears in scene_description or image_prompt
    # but their description's leading phrase isn't visible in the
    # image_prompt, append the full description so the renderer has it.
    if session.table_id and image_prompt:
        characters = PlayerCharacter.query.filter_by(
            table_id=session.table_id
        ).all()
        prompt_lower = image_prompt.lower()
        desc_lower = (scene_description or '').lower()
        mentioned = [
            pc for pc in characters
            if pc.name.lower() in desc_lower
            or pc.name.lower() in prompt_lower
        ]
        addenda = []
        for pc in mentioned:
            desc = (pc.description or '').strip()
            if not desc:
                continue
            # Sniff the first descriptive phrase from the description and
            # check if anything close to it landed in image_prompt. If
            # not, append the full description.
            sniff = desc.split(',')[0].strip().lower()[:30]
            if sniff and sniff not in prompt_lower:
                addenda.append(f'{pc.name} ({desc})')
        if addenda:
            image_prompt += (
                ' Character details: ' + '; '.join(addenda) + '.'
            )

    # Per-style negative additions. Each style has its own most-common
    # failure mode (Comic Book → photograph; Watercolor → contemporary
    # clothing; etc.). Append directly so the negative is always present
    # regardless of how Claude phrased the prompt. The NO_TEXT_SUFFIX is
    # added inside _generate_fal as a universal anti-typography rule.
    style_neg = STYLE_NEGATIVES.get(_normalize_style(session.art_style) or '')
    if style_neg and image_prompt:
        image_prompt += f', {style_neg}'

    image_url = None
    scene_obj = None

    if scene_changed and image_prompt and not skip_image:
        try:
            gen_result = generate_image(
                session=session,
                prompt=image_prompt,
                scene_description=scene_description,
                transcript_chunk=transcript,
                caption=caption,
                location=location,
                subject_category=subject_category,
                location_label_short=location_label_short,
            )
            image_url = gen_result.get('image_url')
            scene_obj = gen_result.get('scene')
            # Quality signal: passive flow is NOT positive feedback. A
            # distracted DM and a happy DM both let images run; the score
            # should only move "good" when the DM actively says so
            # (thumbs-up = -15) and "bad" when the DM intervenes
            # (correction = +20, regen = +10). Doing nothing should be
            # NEUTRAL. No score change on natural scene flow.
        except Exception:
            logger.exception('Image generation failed')

    # Compute location_changed: did the new scene's location string
    # differ from the last one? Used by the front-end "new location"
    # ping. We compare normalized values, so a re-echo of the same
    # location doesn't fire a ping.
    final_location_changed = bool(
        scene_changed
        and location
        and (last_location or '').strip().lower() != (location or '').strip().lower()
    )

    return {
        'scene_changed': scene_changed,
        'scene_description': scene_description,
        'image_url': image_url,
        'scene': scene_obj,
        'location_changed': final_location_changed,
        'location_label_short': location_label_short,
        'location': location,
    }
