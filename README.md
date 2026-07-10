# Town Scryer

Ambient AI scene art for tabletop RPG sessions -- passively listens to your table and paints evolving scene art on a TV behind the DM. Free and self-hosted.

## Quick Start

```bash
cp .env.example .env    # then edit secrets/keys
docker compose up --build
```

You'll need an `ANTHROPIC_API_KEY` (scene extraction) and an `IMAGE_GEN_API_KEY` (image generation) in your `.env`. Transcription runs on self-hosted Whisper -- no key needed.

| Service     | URL                    |
|-------------|------------------------|
| Web app     | http://localhost:3151   |
| API         | http://localhost:5151   |
| phpMyAdmin  | http://localhost:8080   |

## Documentation

- [SPEC.md](SPEC.md) -- product specification and architecture
- [BRIEF.md](BRIEF.md) -- original project brief

## License

[MIT](LICENSE)
