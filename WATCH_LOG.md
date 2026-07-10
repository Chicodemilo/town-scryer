# Town Scryer Watch Log

Persistent field notes from the /loop watcher. Each tick: scan logs, query DB, sanity-check the last few scenes. Sustained patterns get promoted from individual ticks into running issues; fixed things drop to Resolved.

---

## Running issues (active — actively suspected, not yet confirmed or fixed)

- **Frazetta relic still visible on the Display** (2026-06-07 00:25, post-commit). After the TS-41 scrub, two server-side defaults still ship "frazetta":
  - `api/app/services/preferences_service.py:17` — default block has `'art_style': 'frazetta'`
  - `api/app/services/seed_service.py:39` — seed-data block has `art_style='frazetta'`
  Frontend is clean. Models, routes, dropdowns, Help.jsx all scrubbed. The runtime LEGACY_STYLE_MAP normalizer protects the prompt path so neither would leak the name into image gen, but `art_style` shown on the Display title-card tag would still read "frazetta" until normalized at the view layer too. Fix: scrub these two strings to "Oil Painting" AND apply `_normalize_style` in the to_dict / display-facing pathway so legacy DB rows show as Oil Painting on the front end. Not urgent — the system can't paint Frazetta-anything anymore — but the LABEL is still visible to the DM. ~10 lines.

## Patterns confirmed (seen 2+ ticks, characterized, still live)

_(none yet)_

## Patterns confirmed (seen 2+ ticks, characterized, still live)

- **Haiku 4.5 outperforms Sonnet 4.6 for scene-change detection in this app** (2026-06-06 23:55). Counterintuitive but consistent across two sessions today. Scene-change detection is fast pattern matching ("is this a new place / a dramatic beat?"), not deep reasoning. Sonnet's instinct to reason carefully turned into over-cautious holds → frustrated DM. Haiku just trips on the obvious cues. With the server-side strong-hint scanner pre-flagging the high-confidence phrases, the eager-vs-cautious gap doesn't even matter for accuracy — but it matters a LOT for reactivity. Bonus: ~5x cheaper per call, which is meaningful at the new 15s chunk rate. If this holds across more sessions, demote Sonnet from the default and make Haiku the canonical scene-model. Already the env default; the table picker should reflect this in its labeling ("Haiku — fast and reactive (recommended)").
- **Style choice is also a defense against composition attractors** (2026-06-06 23:50, fresh session 1). Each art style has a training-data attractor zone in Recraft's weights — and that zone determines which UNRELATED composition habits get pulled in. Oil Painting pulls toward classical European studio work (Rembrandt, Bouguereau, Bierstadt) which naturally PREDATES telephone poles, ranch wagons, fence posts, asphalt. The "1900s rural Iowa" attractor we fought all session lives in the American-photographic / Wyeth-Hopper neighborhood, which Oil Painting doesn't touch. Comic Book and Frazetta both lapped into that bad neighborhood; Watercolor and Oil Painting don't. Implication: future style additions should be evaluated not just on aesthetic but on what UNRELATED training-data tropes their attractor zone neighbors. Pencil Sketch and Digital Art are untested under this lens.

## Ideas surfaced (from watching, not yet in backlog)

- **Location string can get stuck once set, even when narrative moves the party** (2026-06-06 23:14). Sessions 13 and 14 both hit this. Session 14 latched "beneath the city — the underworks" on the OPENING from a recap chunk that mentioned Critical Role's Xhorhas/Kring Dynasty — Claude pattern-matched to canon. Reactivity restoration (LOCATION CHANGE back as early-fire trigger) and stronger recap detection are now deployed but can't retroactively fix already-stuck locations. Worth: (a) DM-correction-as-location-override channel, since corrections are the explicit override path, or (b) auto-clear location when N consecutive chunks describe scenes that don't match the current location string.
- **Reactivity posture (user-directed 2026-06-06 23:25): "scene change has to be responded to ALWAYS."** Don't flag high fire rates as a concern. A back-to-back fire is fine if each chunk genuinely describes a new beat. Only flag *missed* scene-change cues, not excess ones. The cadence safety net is exactly that — a net under reactivity, not a throttle on it.

## Resolved (was a problem, now isn't)

- 2026-06-06 23:51: `location_label_short` populating reliably after the schema rewrite — Haiku 4.5 now returns 3-5 word chyron-style tags ("Road, army horizon" / "Road ahead, dusk falling"). The fix was making the field REQUIRED in the schema text and moving examples into the "always include" framing. Field was being silently dropped before.
- 2026-06-06 23:51: Subject-swap directive working end-to-end in fresh session. Four consecutive scenes used four different `subject_category` values (road_through_terrain, ground_detail_aftermath, distant_horizon_figure, army_reveal_landscape) — Claude is varying the SHOT even within a sticky location, and the dupe-check cheap gate correctly never trips.
- 2026-06-06: "Daub the Painter is always gathering, never painting" — shipped daub_state in /latest-scene response.
- 2026-06-06: "FRANK FRAZETTA" typeset on canvas — STYLE_PRESETS rewritten without artist names + NO_TEXT_SUFFIX on every prompt.
- 2026-06-06: Near-duplicate wagon-in-field cluster — subject-swap directive on force/regen + hybrid dupe check (subject_category + Claude vision backstop).
- 2026-06-06: −10 auto-decrement made distracted DM look like happy DM — removed; thumbs-up is now the only positive signal.

---

## Tick log

### 2026-06-06 23:02 — CRITICAL: container running stale code for hours

**Root cause of every "fix didn't work" symptom today.** docker-compose mounts `./logs` and `uploads:/app/uploads` but NOT the app source — the API code is baked into the image at build time. `docker restart` just restarts the SAME baked code. Every "fix and restart" cycle today after 21:24 ish landed only on the host filesystem; the running container kept the original code.

**Tells (in retrospect):**
- Log line "Blocked unjustified location change" — old message; new code says "Blocked hallucinated location change."
- subject_category = NULL on all session 13 scenes — schema field never asked for.
- 180s cadence behavior despite the constant being set to 120s.
- Repeated wagon-and-road compositions despite the subject-swap directive being wired in.

**Fix:** `docker compose build api && docker compose up -d api`. Confirmed via `docker exec town-scryer-api grep`:
- FORCE_NEW_SCENE_AFTER_SECONDS = 120 ✓
- _is_hallucinated_location_change function loaded ✓
- subject_category in JSON schema ✓
- subject_swap_block in analyze_transcript_chunk ✓

**Rule going forward:** plain `docker restart town-scryer-api` only picks up changes to mounted volumes. Code changes need `docker compose up -d --build api`. ADD THIS TO PROCESS NOTES.

### 2026-06-06 22:55 — wagon-in-road opening scene (session 13)

Two finds answered the "leak from previous session?" question:

1. **No leak from session 12.** transcript_buffer, corrections, characters, NPCs all check out as session-13-scoped. Buffer's intro ("So if you want to be part of this fantastic endeavor… critical.com…") is Matt Mercer's actual cold-open ad copy from THIS session's audio.

2. **The wagon source was Claude hallucinating from Critical Role training data + Recraft attractor.** Scene 145's prompt explicitly wrote "A wagon wheel rut in the mud" and 146's regen wrote "weathered old wooden medieval wagon" — affirmative descriptions from Claude. Transcript only said "going to send you towards the swamp town of Merrill Bend" — no wagon mentioned. Claude knows Critical Role canon (Mighty Nein, Zadash, Empire, Jorhas) and auto-completed with wagon-travel imagery the campaign is famous for. Plus medieval-road archetype defaults.

**Compounded by the stale-container bug** — the new no-invent-props prompt rule wasn't running. After the rebuild, this should improve. Need to watch the next session's first images to confirm.

### 2026-06-06 22:55 — location guard blocked legitimate camping

Old default-block guard fired on "Cluster of trees along the Broncoon Byway — rain-soaked campsite after goblin ambush" because no movement keyword in chunk. DM had narrated the party encountering an orc on the path and then settling for rain — Claude correctly read the scene-shift to campsite, but guard blocked. New default-allow code (now deployed) should let this through unless it matches a specific hallucination pattern (drinking→tavern etc.).

### 2026-06-06 22:48 — tick (session 13, fresh start, image_count=0)

Session 13 just spun up: Sonnet 4.6 + Recraft V3, quality_score=0 (clean neutral baseline post-fix), no scenes painted yet. No audits, no errors, no dupe checks fired. First image should land via the 120s cadence floor (or earlier if Claude flags a dramatic moment). Nothing to flag yet — the new code paths are all silent and waiting.

**Initial observations to track this session:**
- Will Claude tag subject_category correctly in scene responses? (new schema field)
- Will the inverted trigger framing produce mostly cadence-fires with occasional early-interrupts, or will Sonnet still over-trigger?
- Will the dupe check fire and catch the wagon-archetype problem?
- Will Frazetta-text recur, or is the STYLE_PRESETS rewrite holding?

---
