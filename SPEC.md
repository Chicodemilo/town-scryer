# Town Scryer — Product Spec

*2026-06-01*

## What It Is

A web app that passively listens to a tabletop RPG session and renders evolving scene art on a TV behind the DM — updating automatically as the narration moves the party through the world. Nobody types prompts. Nobody stops the game. The screen just *knows*.

## User Flow

### 1. Landing Page
Atmospheric D&D visuals selling the experience. Demo reel of generated scenes. "Your table just got a window into the world."

### 2. Sign Up
Email + verification required. No anonymous usage.

### 3. Session Setup (first run or new session)
All have sensible defaults — user can start immediately or fine-tune:
- **Game type** — Fantasy D&D (default), sci-fi, horror, western, etc.
- **Art style** — Frazetta, watercolor, comic, sketch, retro AD&D, etc.
- **Gore level** — PG-13 (default), PG, R

### 4. Tables (Party Management)
- DM creates a **Table** and gets an invite code (6-char, easy to say out loud)
- Players join via code
- Each player manages their own character: name, description, optional portrait upload
- DM sees all player characters; they feed into scene generation prompts
- Players can view all session art from their Table's sessions
- DM can run sessions for any of their Tables
- A DM can have multiple Tables (different campaigns/groups)

### 5. In-Session
- Hit **Start** — mic goes live, scenes begin generating
- **Pause** — stops listening and generating
- **Resume** — picks back up
- Fullscreen display mode for the TV (separate URL/tab, no UI chrome)

### 6. Post-Session
- Session saved to campaign archive, images browsable
- Persistent party characters across sessions

## Architecture (high level)

### Starting Point
Fork `starting_point_2025` boilerplate (Flask + React + Vite + Docker Compose + MySQL).

### Ported audio pipeline
The audio capture → transcription → API pipeline, ported from an earlier project:
- Web Speech API mic capture in browser
- 30-second transcript chunking
- POST to backend API
- Claude API call for scene extraction
- Swap the original text response for an image generation call

### Key Models (new)
- **Session** — start/pause/resume, image count, duration tracking, linked to user
- **Scene** — generated image + prompt + timestamp, linked to session
- **PlayerCharacter** — name, description, portrait upload, linked to user
- **UserPreferences** — game type, art style, gore level defaults

### Key Integrations
- **Anthropic Claude API** — scene extraction from transcripts
- **Image generation API** — TBD (DALL-E 3, Stable Diffusion, Flux, etc.)

## Competitive Landscape

**No direct competitors.** Adjacent tools:
- D&D Beyond, Roll20, Foundry VTT, Owlbear Rodeo — game mechanics, not ambient art
- Midjourney / DALL-E — manual prompt-and-wait, not passive/automatic

The differentiator is **passive, real-time, voice-driven scene art**. Nobody else does this.

## Build Path

- **v1:** Scene art only. No character consistency. Core loop: listen → extract → generate → display.
- **v2:** Party portraits. Character descriptions/uploads influence generated scenes. IP-Adapter / reference-image consistency.
- **v3:** Style packs, campaign archive enhancements, per-encounter triggers, possibly sound/music.
