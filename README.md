# GenAI Whiteboard Explainer MVP

Web-only MVP that turns **PDFs** or **plain-text prompts** into an English **whiteboard-style** explainer video:

- **Quick mode**: 2–3 scenes (fast)
- **Deep mode**: 8–10 scenes (more coverage)
- **720p output** (1280×720)
- **Parallel rendering**: one Celery task per scene (Playwright → MP4) + final concat step
- **Live progress**: API streams worker events via SSE; UI shows per-scene status

## How it works (high level)
1) Ingest PDF or prompt text
2) Supervisor creates an outline + scene objectives (LLM when available, offline fallback)
3) For each scene (in parallel):
   - generate a short script
   - synthesize narration (**TTS fallback order: OpenAI → Google → offline eSpeak**)
   - build a scene SVG + wrap to HTML
   - render HTML → MP4 via Playwright (Chromium)
4) Concatenate scene MP4 clips into a final MP4 + generate SRT

## Local run (Docker)
```bash
cd infra
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000

### Auth
This MVP uses a simple token for local dev.

- Default token: `dev-token`
- Set it via env `DEV_TOKEN` (API + worker)

The frontend expects the same token and stores it locally.

## Environment variables
Recommended: copy `.env.example` → `.env` and fill keys.

Required for “best” quality:
- `OPENAI_API_KEY` (narration + LLM fallback)

Optional:
- `GOOGLE_APPLICATION_CREDENTIALS` (Google Cloud TTS)

## Important note (schema)
The database is auto-created on startup. If you previously ran an older schema, delete the persisted DB volume/file:

- Docker: remove `../data` (or the Postgres volume) if you want a clean slate
- Local sqlite: delete `data/app.db`

## Key endpoints
- `POST /documents/upload` — upload PDF
- `POST /documents/prompt` — create a “document” from plain text
- `POST /jobs` — start generation
- `GET /jobs/{job_id}` — status, artifacts, segments
- `GET /jobs/{job_id}/stream` — SSE event stream (scene progress)
- `GET /assets/{asset_id}` — download/view artifacts

## What’s in the box
- `apps/api` — FastAPI backend
- `apps/worker` — Celery worker (parallel scene rendering)
- `frontend` — Next.js UI (progress, preview, artifact downloads)
- `core` — ingestion, planning, whiteboard rendering, TTS routing
