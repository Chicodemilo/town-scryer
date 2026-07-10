# Town Scryer — Brief

*Working brief, 2026-05-31*

## One line

A website that passively listens to a D&D session and renders an evolving scene on the TV behind the DM — torch-lit dungeon, smoky tavern, foggy forest — updating as the narration moves the party through the world.

## Shape

- **Deployment:** Web app open in a browser on the DM's laptop, fullscreened to an HDMI-connected TV behind the DM. Players see the screen across the table; nobody has to look at a phone.
- **Input:** Microphone in the room. Audio is chunked (~30 seconds at a time) and sent to an LLM for transcription + scene extraction.
- **Output:** An image generation call per scene change, rendered fullscreen. The image holds until the next scene change is detected.
- **Customization:**
  - **Style presets** — Frazetta, comic, sketch, watercolor, retro AD&D, etc. Style is locked per session so the table's "look" is consistent.
  - **Party references** — players can upload hand-drawn portraits of their characters, or describe them in text. The system uses these as image-gen references so the rogue keeps looking like *your* rogue.
- **Refresh logic (open question):** Time-based + voice-cue detection ("the party enters...", "you arrive at...", combat begins, etc.) is the obvious first try. Latency on image gen (5–30s) makes this non-trivial — the trick is detecting *early* enough that the image lands when the narration does, not after.

## Origin

The architecture is lifted wholesale from an earlier AI screen-character project that already ran on a home Ubuntu server and did exactly the right thing:

- Captures 30-second audio chunks from the room
- Sends to the Anthropic API
- Receives back commentary that the character speaks/displays on-screen

Town Scryer is the same backbone with one swap: **the output goes to an image generation call instead of a text/voice commentary call**, and the result is painted fullscreen instead of spoken. Everything upstream of that — mic capture, chunking, transmission, the local site hosting — was already working code.

This is why the build is cheap. The hard infrastructure already existed for an unrelated use case. The MVP is a Saturday: fork the capture pipeline, replace the text-return step with an image-return step, render the result in a fullscreen browser window.

## Shipping path

- **v1:** Scene art only. No party portraits, no character consistency. Tavern, dungeon, forest, boss room. Already a magic-trick experience — the wow is in "the scene changes as we play."
- **v2:** Party portraits. Hand-drawn or described characters appear in the scenes. This is where the hard problem lives — image-gen models drift on faces across scenes, so v2 needs an IP-Adapter / LoRA / reference-image trick to make the rogue stay the rogue. Worth a build test before promising it.
- **v3:** Style packs, campaign archive ("save your campaign's art"), maybe per-encounter triggers (combat music? boss reveals?). All optional.

## Real questions before committing

1. **Refresh logic** — voice-cue detection + time-based fallback is plausible but needs prototype data on how it actually feels at the table.
2. **Character consistency** — known hard problem; v1 dodges it, v2 has to solve it. How hard is it really with current reference-image tooling? Worth a small test before promising the feature.
3. **Per-session API cost** — a 4-hour session with refreshes every couple minutes adds up fast.
4. **Competitive landscape** — a few Roll20/Foundry plugins exist in adjacent space, but ambient + passive listening + style-locked party + TV-behind-the-DM staging is a real differentiator if executed well.

## Status

Captured 2026-05-31, before any code existed. Kept as the original project brief.
