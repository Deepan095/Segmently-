# Segmently

> Turn one long video into a week of short-form clips.

**Segmently** is a small SaaS app that takes a long‑form video (a podcast, webinar, talk,
or stream — anywhere from 10 minutes to a few hours), transcribes it, uses an LLM to find
the moments that stand on their own, and renders each one as a vertical **9:16 ~1‑minute
clip with burned‑in captions**, ready to post as a YouTube Short, Instagram Reel, or
TikTok. Optional stock‑footage B‑roll can be layered over the talking head.

- **Live site:** https://segmently.online
- **Repo:** https://github.com/Deepan095/Segmently-
- **Status:** MVP, running in production. Payments, direct social publishing, and email
  notifications are deliberately out of scope (see [What's in / out](#whats-in--out)).

This README is written for someone who has never seen the project before. It covers the
whole story: how the app was generated from a template using Claude Code, what every
folder is for, how to run it on your own machine, how the video pipeline works, and how
it is deployed.

---

## Table of contents

1. [What Segmently does](#what-segmently-does)
2. [How this project was built (the template + agent workflow)](#how-this-project-was-built)
   - [The three source-of-truth files: `INITIAL.md`, `CLAUDE.md`, `PRPs/`](#the-three-source-of-truth-files)
   - [`skills/` — reusable code patterns](#skills--reusable-code-patterns)
   - [`agents/` — who does what](#agents--who-does-what)
   - [`.claude/commands/` — the three slash commands](#claudecommands--the-three-slash-commands)
   - [The build in three phases](#the-build-in-three-phases)
3. [Architecture](#architecture)
4. [Repository layout](#repository-layout)
5. [Prerequisites](#prerequisites)
6. [Run it locally with Docker (recommended)](#run-it-locally-with-docker-recommended)
7. [Run it locally without Docker](#run-it-locally-without-docker)
8. [Environment variables](#environment-variables)
9. [How the video pipeline works](#how-the-video-pipeline-works)
10. [Using the app](#using-the-app)
11. [Testing](#testing)
12. [Deploying to a server](#deploying-to-a-server)
13. [Troubleshooting](#troubleshooting)
14. [Tech stack](#tech-stack)
15. [Contributing & conventions](#contributing--conventions)
16. [What's in / out](#whats-in--out)

---

## What Segmently does

From a user's point of view:

1. **Sign up / log in** — email + password, or "Sign in with Google" (when configured).
2. **Create a project** — upload a video file, or paste a link (YouTube, Vimeo, Twitch,
   TikTok, and other supported platforms, or a direct `.mp4`/`.mov` URL).
3. **Wait a few minutes** — Segmently downloads the source, transcribes the audio, asks an
   LLM to pick the best self‑contained ~1‑minute moments, and renders each as a vertical
   clip. You watch the progress bar move through the pipeline stages.
4. **Review the clips** — each clip has a preview player, an **interest score (0–100)**
   with a one‑line reason, an editable caption, and a crop/reframe control.
5. **Tweak & re‑render** — edit the caption text or trim points and Segmently re‑renders
   that clip.
6. **Download** — grab the finished MP4 via a signed, expiring link.

There is also a **dashboard** (minutes processed, clips generated, usage charts) and an
**admin panel** (user management, job monitoring, retry failed jobs) for `is_admin` users.

---

## How this project was built

Segmently did not start as a blank folder. It started from a **MicroSaaS template** that
is designed to be driven by [Claude Code](https://claude.com/claude-code) (Anthropic's
CLI coding agent). The idea of the template:

> You describe the product in plain English → Claude turns that into a build plan → a set
> of specialised agents build the backend, frontend, database, infra, tests, and security
> review in parallel.

The files that make this work are all still in the repo, so you can see exactly how it
was done — and re‑run the same flow for a different product.

### The three source-of-truth files

| File | What it is | Who reads it |
|---|---|---|
| **`INITIAL.md`** | The **product definition**. Name, target user, tech‑stack choices, every module with its data models, API endpoints and pages, the MVP scope, acceptance criteria, and security requirements. This is the human‑written spec. | You write it (or the `/setup-project` wizard writes it for you). `/generate-prp` reads it. |
| **`CLAUDE.md`** | The **project rules**. Coding standards (type hints, docstrings, no `any`), forbidden patterns (`no print()`, no plaintext passwords, never run rendering inside a request), API conventions, auth config, env‑var list, module‑specific business rules, commit‑message format. | Claude Code reads this **automatically** on every session in this repo. Every agent follows it. |
| **`PRPs/segmently-prp.md`** | The **PRP** ("Product Requirements Prompt") — the generated build blueprint. It maps each module to the agents that build it, lists every model/endpoint/page in table form, and defines the phase plan and validation gates. | Generated by `/generate-prp`. Consumed by `/execute-prp`. |

Read them in that order (`INITIAL.md` → `CLAUDE.md` → `PRPs/segmently-prp.md`) and you'll
understand the whole product before touching a line of code.

### `skills/` — reusable code patterns

Each skill file is a focused "how we do X in this codebase" reference with copy‑paste‑ready
snippets. Agents are told to **read the relevant skill before writing code**, which keeps
the output consistent.

| Skill | Covers |
|---|---|
| `skills/DATABASE.md` | SQLAlchemy models, `Base`, timestamp mixins, relationships, Alembic setup & migrations |
| `skills/BACKEND.md` | FastAPI app structure, routers/services/schemas split, JWT + Google OAuth, custom exceptions, error envelope |
| `skills/FRONTEND.md` | React + Vite + TS structure, the UI kit (`GlassCard`, `GradientButton`, `MeshBackground`, …), the Axios client, auth context |
| `skills/TESTING.md` | `pytest` fixtures (in‑memory DB, test client, fakes), Vitest + React Testing Library setup |
| `skills/DEPLOYMENT.md` | Dockerfiles, `docker-compose`, GitHub Actions CI |

### `agents/` — who does what

The `/execute-prp` command runs Claude as an **ORCHESTRATOR** that dispatches specialised
sub‑agents. Each agent's role, inputs, and outputs are defined in `agents/`:

| Agent | Responsibility |
|---|---|
| `agents/ORCHESTRATOR.md` | Breaks the PRP into tasks, launches the other agents in parallel, runs the validation gates, assembles the result |
| `agents/database-agent.md` | All SQLAlchemy models + the Alembic migration |
| `agents/backend-agent.md` | FastAPI foundation, then per‑module API endpoints, services, and the background worker / media pipeline |
| `agents/frontend-agent.md` | Vite setup + UI kit, then per‑module pages and components |
| *DevOps* (in the command prompt) | Dockerfiles, compose files, `.env.example`, CI |
| *Test* (in the command prompt) | `pytest` + Vitest suites, 80%+ backend coverage |
| *Review* (in the command prompt) | OWASP‑style security pass + code‑quality review |

### `.claude/commands/` — the three slash commands

These are custom Claude Code commands (Markdown prompt files). You run them by typing
`/name` in a Claude Code session opened in this repo.

| Command | What it does |
|---|---|
| **`/setup-project`** | Interactive wizard. Asks about your product, tech‑stack, and modules, then writes `INITIAL.md` and `CLAUDE.md` for you. |
| **`/generate-prp INITIAL.md`** | Reads `INITIAL.md` + `CLAUDE.md`, produces `PRPs/<name>-prp.md` — the build blueprint with the phase plan. |
| **`/execute-prp PRPs/<name>-prp.md`** | Acts as the ORCHESTRATOR and builds the whole app in three phases (below). |

### The build in three phases

```
INITIAL.md ──/generate-prp──▶ PRPs/segmently-prp.md ──/execute-prp──▶ working app
```

```
Phase 1 — Foundation (4 agents in parallel)
  ├─ database  → models/*, database.py, alembic/ + 0001_initial migration
  ├─ backend   → main.py, config.py, dependencies.py, exceptions.py, routers/schemas/services skeleton
  ├─ frontend  → Vite + TS project, Tailwind, UI kit, Axios client, router
  └─ devops    → backend/ & frontend/ Dockerfiles, docker-compose*.yml, .env.example, CI
  ── gate: pip install • alembic upgrade head • npm install • docker compose config

Phase 2 — Modules (backend + frontend pair, per module, in parallel)
  ├─ Auth        → JWT + refresh rotation + Google OAuth  |  Login/Register/Profile pages
  ├─ Projects    → upload / URL import + pipeline trigger  |  project list & detail, upload dropzone
  ├─ Clips       → list / detail / edit / re-render / download  |  clip library, player, caption editor
  ├─ Dashboard   → summary / usage / top-clips endpoints  |  dashboard widgets & charts
  └─ Admin       → users / stats / jobs endpoints (is_admin) |  admin pages behind a guard
  ── gate: ruff check • npm run lint • npm run type-check

Phase 3 — Quality (3 agents in parallel)
  ├─ tests   → pytest + Vitest, 80%+ backend coverage
  ├─ review  → security + code-quality report
  └─ research→ best-practice validation
  ── final gate: full test suite • docker compose build • GET /health
```

After Phase 3 the app was refined by hand (the media pipeline hardening, the fit/crop
render modes, windowed segmentation, B‑roll, the landing page, and the production
deployment) — those changes are in the git history.

---

## Architecture

```
                         ┌──────────────┐
   Browser ──────────────▶│   web (SPA)  │  React + Vite, served by nginx
                         └──────┬───────┘
                                │ /api/v1/*
                         ┌──────▼───────┐        ┌───────────┐
                         │  api (FastAPI)│───────▶│ PostgreSQL│  users, projects, clips, jobs
                         └──────┬───────┘        └───────────┘
                                │ enqueue job
                         ┌──────▼───────┐        ┌───────────┐
                         │    Redis      │◀──────▶│  worker   │  arq async queue
                         └───────────────┘        └─────┬─────┘
                                                        │
                       download → transcribe → segment → render (FFmpeg)
                                                        │
                                                  ┌─────▼──────┐
                                                  │  MinIO / S3 │  source videos + rendered clips
                                                  └────────────┘
                                                        ▲
                        OpenAI API (transcription + segment selection)
                        Pexels API (optional B-roll footage)
```

- **`api`** never does heavy work in a request. It writes a row and enqueues a job (HTTP
  `202 Accepted`); the client polls project/job status.
- **`worker`** and **`api`** are built from the **same** image (`backend/Dockerfile`), so
  FFmpeg and the transcription libraries are available to both. Only the worker uses them.
- **Clip URLs** handed to the browser are **signed and expiring** — the bucket is never
  publicly listable.

---

## Repository layout

```
Segmently-/
│
├── INITIAL.md                  # product definition (the human spec)
├── CLAUDE.md                   # project rules Claude Code follows automatically
├── README.md                   # you are here
├── DEPLOY.md                   # full VPS deployment runbook
│
├── .claude/commands/           # /setup-project, /generate-prp, /execute-prp
├── agents/                     # ORCHESTRATOR + database/backend/frontend agent specs
├── skills/                     # DATABASE / BACKEND / FRONTEND / TESTING / DEPLOYMENT patterns
├── PRPs/segmently-prp.md       # generated build blueprint
│
├── backend/                    # FastAPI app + arq worker (one image, backend/Dockerfile)
│   ├── app/
│   │   ├── main.py             # FastAPI app: CORS, exception handlers, router registration
│   │   ├── config.py           # Pydantic Settings; refuses insecure defaults when DEBUG=false
│   │   ├── database.py         # engine, SessionLocal, get_db
│   │   ├── dependencies.py     # get_db, get_current_user
│   │   ├── models/             # User, RefreshToken, Project, Transcript, ProcessingJob, Clip, ClipCaption
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── routers/            # auth, projects, clips, dashboard, admin  (all under /api/v1)
│   │   ├── services/           # business logic: storage, transcription, segmentation, rendering, broll, ssrf
│   │   ├── workers/            # arq pipeline: run_download → run_transcribe → run_segment → run_render
│   │   └── auth/               # jwt.py, oauth.py, seed.py
│   ├── alembic/                # migrations (0001_initial.py creates everything)
│   ├── scripts/seed.py         # creates the admin user from ADMIN_EMAIL / ADMIN_PASSWORD
│   ├── tests/                  # pytest suite (in-memory SQLite, all externals faked)
│   └── requirements.txt
│
├── frontend/                   # React + Vite + TypeScript SPA
│   ├── src/
│   │   ├── main.tsx, App.tsx   # router; "/" is the public LandingPage
│   │   ├── pages/              # LandingPage, Login, Register, Dashboard, Projects, Clips, Admin, …
│   │   ├── components/         # ui/ (GlassCard, GradientButton…), layout/, auth/, projects/, clips/, admin/
│   │   ├── hooks/              # useAuth, useProjects, useClips, useDashboard, useAuthProviders…
│   │   ├── services/           # api.ts (Axios + interceptors) + one *Service.ts per module
│   │   ├── context/AuthContext.tsx
│   │   └── types/
│   ├── nginx.conf              # SPA fallback + /api proxy for the production image
│   └── package.json
│
├── docker-compose.yml          # full local stack: db, redis, minio, createbuckets, api, worker, web
├── docker-compose.dev.yml      # dev override: bind mounts + hot reload
├── .env.example                # copy to .env for local runs
│
├── deploy/
│   ├── docker-compose.prod.yml # production overlay (integrates with an existing Traefik proxy)
│   ├── .env.prod.example       # copy to deploy/.env.prod on the server
│   ├── segmently.sh            # up | update | migrate | seed | logs | ps | backup | down
│   └── cookies/                # optional YouTube cookies.txt mount (see Troubleshooting)
│
└── .github/workflows/ci.yml    # CI: ruff + pytest, eslint + tsc + build, docker compose build
```

---

## Prerequisites

**To run with Docker (the easy path):**

- **Docker Engine 24+** with the **Docker Compose v2 plugin** (`docker compose`, not the
  old `docker-compose`). Docker Desktop on Windows/Mac includes both.
- ~4 GB free RAM and ~10 GB free disk for images + volumes.
- An **OpenAI API key** if you want fast transcription and the AI segment selection
  (`https://platform.openai.com/api-keys`). Segment selection needs it; transcription can
  fall back to a local model.
- *(optional)* A free **Pexels API key** for B‑roll (`https://www.pexels.com/api/`).
- *(optional)* A **Google OAuth client** if you want the "Sign in with Google" button.

**To run without Docker, additionally:**

- **Python 3.11+**
- **Node.js 20+** and npm
- **PostgreSQL 16**, **Redis 7**, and an S3‑compatible store (or MinIO)
- **FFmpeg + ffprobe** on your `PATH` (the worker shells out to them)

---

## Run it locally with Docker (recommended)

From the repo root:

```bash
# 1. Get the code
git clone https://github.com/Deepan095/Segmently-.git segmently
cd segmently

# 2. Create your env file (defaults already target the compose network)
cp .env.example .env

# 3. Edit .env — the one thing worth setting now:
#    OPENAI_API_KEY=sk-...           (needed for AI segment selection)
#    Optionally: TRANSCRIPTION_BACKEND=openai   (faster than the local model)
#    Everything else works as-is for local dev.

# 4. Build and start everything
docker compose up -d --build

# 5. Create the object-storage bucket (one-shot; also runs automatically)
docker compose run --rm createbuckets

# 6. Apply database migrations
docker compose exec api alembic upgrade head

# 7. Create the admin user (uses ADMIN_EMAIL / ADMIN_PASSWORD from .env)
docker compose exec api python -m scripts.seed
```

Now open:

| What | URL | Notes |
|---|---|---|
| **Web app** | http://localhost:3000 | The SPA |
| **API** | http://localhost:8000 | Health check at `/health` |
| **API docs** | http://localhost:8000/docs | Interactive OpenAPI (Swagger) |
| **MinIO console** | http://localhost:9001 | Login `minioadmin` / `minioadmin` |

Log in with the admin credentials from your `.env`
(defaults: `admin@segmently.dev` / `dev-admin-change-me`).

### Everyday Docker commands

```bash
docker compose logs -f api worker        # tail logs (watch a pipeline run here)
docker compose exec api bash             # shell into the API container
docker compose exec api alembic upgrade head
docker compose ps                        # service status
docker compose down                      # stop everything
docker compose down -v                   # stop AND wipe all data (db/redis/minio volumes)
```

### Hot-reload development

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This bind‑mounts `backend/` and `frontend/`, runs `uvicorn --reload` and `arq --watch`,
and swaps the nginx `web` container for the Vite dev server (still on
http://localhost:3000).

---

## Run it locally without Docker

You need PostgreSQL, Redis, MinIO (or S3), and FFmpeg running yourself, then:

```bash
# --- Backend API ---
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env        # then edit: point DATABASE_URL / REDIS_URL / STORAGE_* at your local services
alembic upgrade head
python -m scripts.seed
uvicorn app.main:app --reload  # http://localhost:8000

# --- Background worker (separate terminal, same venv, FFmpeg on PATH) ---
cd backend
arq app.workers.settings.WorkerSettings

# --- Frontend (separate terminal) ---
cd frontend
npm install
npm run dev                    # http://localhost:5173 (Vite default)
```

> When running the frontend on Vite's default port, set `VITE_API_URL=http://localhost:8000`
> in `frontend/.env` and make sure that origin is in `ALLOWED_ORIGINS` for the API.

---

## Environment variables

Local dev reads **`.env`** (copy from `.env.example`). Production reads
**`deploy/.env.prod`** (copy from `deploy/.env.prod.example`). Neither `.env` file is
committed.

| Variable | Purpose | Local default |
|---|---|---|
| `DEBUG` | `true` locally. When `false`, the API **refuses to boot** with default `SECRET_KEY` / `ADMIN_PASSWORD` / DB password. | `true` |
| `SECRET_KEY` | Signs JWTs. Generate with `openssl rand -hex 32`. | `dev-secret-change-me` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Token lifetimes. Refresh rotates & revokes the old token. | `30` / `7` |
| `DATABASE_URL` | PostgreSQL connection string. | points at the `db` service |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose‑managed Postgres. Password must match `DATABASE_URL`. | `segmently` |
| `REDIS_URL` | Queue broker. | `redis://redis:6379/0` |
| `STORAGE_ENDPOINT_URL` | S3/MinIO endpoint the **server** uses. | `http://minio:9000` |
| `STORAGE_PUBLIC_ENDPOINT_URL` | S3/MinIO endpoint the **browser** uses to open signed clip URLs. Must be reachable from the browser. | `http://localhost:9000` |
| `STORAGE_BUCKET` / `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` | Object storage bucket + credentials. | `segmently-media` / `minioadmin` / `minioadmin` |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | The user created by `scripts.seed`. | `admin@segmently.dev` / `dev-admin-change-me` |
| `TRANSCRIPTION_BACKEND` | `local` = faster‑whisper on CPU (no API cost, slow). `openai` = OpenAI audio API (fast, ~$0.006/min). | `local` |
| `WHISPER_MODEL` | `tiny`\|`base`\|`small`\|`medium`\|`large-v3` (local backend only). | `base` |
| `OPENAI_API_KEY` | Required for AI segment selection (and for `TRANSCRIPTION_BACKEND=openai`). | — |
| `OPENAI_MODEL` | Chat model used to pick the clip moments. | `gpt-4o-mini` |
| `BROLL_ENABLED` / `PEXELS_API_KEY` | Opt‑in stock‑footage cutaways. | `false` / — |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth. **Both** must be set or the "Sign in with Google" button is hidden. | blank |
| `GOOGLE_REDIRECT_URI` | Must match the redirect URI registered in Google Cloud. | `http://localhost:8000/api/v1/auth/google/callback` |
| `FRONTEND_URL` / `ALLOWED_ORIGINS` | CORS + the OAuth callback redirect target. | localhost |
| `VITE_API_URL` | Browser‑facing API URL, **baked into the web build at build time**. | `http://localhost:8000` |

Production‑only knobs (`deploy/.env.prod`): `MAX_UPLOAD_BYTES`,
`MAX_SOURCE_DURATION_SECONDS`, `RENDER_MODE` (`fit` blurred‑background vs `crop`),
`FFMPEG_PRESET`, `SEGMENTS_TARGET`, `SEGMENTS_MAX`, `WORKER_CPUS`, `YTDLP_MAX_HEIGHT`.

---

## How the video pipeline works

Every project moves through four background jobs, run by the `worker` off the Redis queue.
The project `status` and each `ProcessingJob` progress are visible in the UI.

| Stage | Job | What happens |
|---|---|---|
| **1. Download** | `run_download` | For a **direct video URL** (`.mp4`/`.mov`/…) it streams the file with SSRF protection (private/internal IP ranges are rejected, every redirect hop re‑validated). For an **allow‑listed platform** (YouTube, Vimeo, Twitch, TikTok, Dailymotion, Streamable, Facebook, Instagram) it uses `yt-dlp`. For an **uploaded file** it just pulls it from storage. The result is validated (must be a real video with a readable duration) and stored in the bucket. |
| **2. Transcribe** | `run_transcribe` | Extracts a mono 16 kHz audio track with FFmpeg, then transcribes it — either with a local faster‑whisper model or the OpenAI audio API, depending on `TRANSCRIPTION_BACKEND`. Produces a `Transcript` with word/segment timings. A video with no audio track fails with a clear message. |
| **3. Segment** | `run_segment` | Splits the transcript into `SEGMENT_WINDOW_SECONDS` (default 600s) windows and asks the LLM to pick roughly one strong self‑contained moment per window (target `SEGMENTS_TARGET`, cap `SEGMENTS_MAX`). Each proposed in/out point is **snapped to real sentence boundaries** and stretched/trimmed to ~45–75s so no clip starts or ends mid‑sentence. Overlapping picks are de‑duplicated (higher score wins). Each surviving pick becomes a `Clip` + `ClipCaption` + a render job. |
| **4. Render** | `run_render` | FFmpeg builds the vertical clip. `RENDER_MODE=fit` puts the source on a blurred, zoomed copy of itself (good for screen recordings / non‑vertical sources); `crop` cover‑crops with an adjustable `reframe_offset`. Captions are chunked into ≤30‑character cues and burned in as ASS subtitles with safe margins. If B‑roll is enabled, the LLM suggests a few short visual cues and Pexels clips are overlaid over those spans while the original audio continues. Output is a clean 1080×1920 H.264 MP4. |

Editing a clip's caption text or trim points sets it back to `queued` and re‑runs
`run_render` for that clip only.

---

## Using the app

1. **Log in** at http://localhost:3000 (or just browse the landing page — it doesn't
   require login until you click **Log in** or **Add new project**).
2. **New project** → paste a link or drop a file → **Create**.
3. Watch the project detail page. Stages light up: `downloading → transcribing →
   segmenting → rendering → completed`.
4. Open a finished clip: play it, read the score reason, edit the caption, adjust the
   crop, hit **Re‑render** if you changed anything, then **Download**.
5. The **Clips** page shows every clip across projects; filter by project, sort by score.
6. **Dashboard** shows your totals and a usage chart. **Admin** (admin users only) lists
   users and processing jobs and can retry failed jobs.

---

## Testing

```bash
# Backend — pytest, in-memory SQLite, every external service faked
cd backend
pytest -q
pytest -q --cov=app --cov-report=term-missing     # with coverage (target 80%+)

# Frontend — Vitest + React Testing Library
cd frontend
npm test

# Linters / type-checks
cd backend  && ruff check .
cd frontend && npm run lint && npm run type-check
```

CI (`.github/workflows/ci.yml`) runs all of the above on every push and pull request,
plus `docker compose build`.

> Known quirk: `tests/test_units_services.py::test_transcribe_no_backend_available`
> assumes `faster-whisper` is **not** installed. It is in `requirements.txt`, so that one
> test fails in a full install. It is not a regression — ignore it; the rest of the suite
> passes.

---

## Deploying to a server

Full step‑by‑step runbook: **[`DEPLOY.md`](DEPLOY.md)**. Short version:

The production stack is the same `docker-compose.yml` **plus** the overlay
`deploy/docker-compose.prod.yml`, which:

- keeps `db`, `redis`, and `worker` internal (no published ports),
- exposes `web`, `api`, and `minio` through an **existing [Traefik](https://traefik.io/)
  reverse proxy** on the host (labels request Let's Encrypt certificates), routing
  `segmently.online` → web, `segmently.online/api` + `/health` → api, and
  `s3.segmently.online` → minio for signed clip URLs.

On the server, once Docker + Traefik are set up and DNS points at the box:

```bash
cd /opt && git clone https://github.com/Deepan095/Segmently-.git segmently && cd segmently

cp deploy/.env.prod.example deploy/.env.prod
# fill in every CHANGE_ME:
#   openssl rand -hex 32   → SECRET_KEY
#   openssl rand -hex 16   → POSTGRES_PASSWORD  (also update DATABASE_URL)
#   openssl rand -hex 12   → STORAGE_ACCESS_KEY
#   openssl rand -hex 24   → STORAGE_SECRET_KEY
#   + OPENAI_API_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, the real domain in the *_URL vars

chmod +x deploy/segmently.sh
./deploy/segmently.sh up          # build + start + migrate + seed
```

Day‑2 operations, all via the helper:

```bash
./deploy/segmently.sh update      # git pull + rebuild + migrate (deploy new code)
./deploy/segmently.sh logs api    # tail one service
./deploy/segmently.sh backup      # gzipped pg_dump into ./backups/
./deploy/segmently.sh ps          # status
./deploy/segmently.sh migrate     # migrations only
```

**Enabling Google sign‑in in production:** create an OAuth client in Google Cloud Console
with redirect URI `https://<your-domain>/api/v1/auth/google/callback`, put the id + secret
in `deploy/.env.prod` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), then
`./deploy/segmently.sh update`. The button appears automatically once both are set.

> `deploy/.env.prod` and any `deploy/cookies/*.txt` are git‑ignored — **never commit
> secrets**. Only `*.example` templates belong in the repo.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| API container restart‑loops, logs say "Insecure default value(s)" | `DEBUG=false` with a `CHANGE_ME` / default still in your env file. Fill them in. |
| Clip plays in the app but download / preview 403s | `STORAGE_PUBLIC_ENDPOINT_URL` must be an address the **browser** can reach (`http://localhost:9000` locally, `https://s3.<domain>` in prod), and that DNS record must exist. |
| Worker stuck at "downloading" a YouTube URL | YouTube blocks datacenter IPs ("Sign in to confirm you're not a bot"). Direct video URLs and file uploads work. To use YouTube, drop a `cookies.txt` at `deploy/cookies/youtube.txt` and set `YTDLP_COOKIES_FILE`. |
| Pasting a YouTube page URL just downloads an HTML file | Old build. Current code routes platform URLs through `yt-dlp`; direct links must end in a video extension. |
| Transcription errors immediately | `TRANSCRIPTION_BACKEND=openai` needs a valid `OPENAI_API_KEY`; `=local` needs FFmpeg and downloads the whisper model on first run (slow, cached afterwards). |
| Renders very slow / out of memory | Small machine. Use `RENDER_MODE=crop` (≈3× faster than `fit`), lower `SEGMENTS_TARGET`, or give the worker more CPUs. |
| `worker` container restarts on a fresh clone before Phase 2 code exists | Not applicable to this repo (the worker module is present); only relevant when regenerating from the template. |
| Google button doesn't appear | Expected unless **both** `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set. Check `GET /api/v1/auth/providers`. |

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0, Pydantic v2, Alembic |
| Queue / worker | Redis + [arq](https://arq-docs.helpmanual.io/) (async task queue) |
| Database | PostgreSQL 16 |
| Object storage | S3‑compatible; MinIO in dev, MinIO‑on‑VPS in the current prod |
| Transcription | `faster-whisper` (local) or OpenAI audio API |
| Segment selection | OpenAI Chat API (JSON mode) |
| Media | FFmpeg (fit/crop reframing, ASS caption burn‑in, B‑roll overlays), `yt-dlp`, Pexels API |
| Frontend | React 18, Vite 5, TypeScript (strict), Tailwind CSS, Framer Motion, TanStack Query v5, React Router v6 |
| Auth | JWT (HS256, 30‑min access + 7‑day rotating refresh), bcrypt, Google OAuth 2.0 |
| Infra | Docker + Docker Compose, nginx (SPA), Traefik (prod TLS), GitHub Actions CI |

---

## Contributing & conventions

- **Read `CLAUDE.md` first.** It lists the coding standards and the forbidden patterns
  (no `print()`, no `any`, no secrets in code, never run transcode/render inside a request
  handler, always issue signed storage URLs, …).
- **Commit message format:**
  ```
  feat(clips): add caption editor
  fix(projects): handle failed URL download
  refactor(workers): extract rendering service
  test(auth): add Google OAuth callback tests
  docs: update README
  ```
- **Before pushing:** `ruff check backend/ && pytest` and
  `cd frontend && npm run lint && npm run type-check && npm run build`.
- **Never commit** `.env`, `deploy/.env.prod`, cookies files, or anything with a real
  key. Only `*.example` templates.

---

## What's in / out

**In (MVP, built and working):**

- Email/password + Google OAuth auth, JWT with refresh rotation
- Project creation from file upload or platform/direct URL
- Auto transcription → AI moment selection → vertical clip rendering with captions
- Optional auto B‑roll
- In‑app preview, caption/trim editing, re‑render, signed MP4 download
- Per‑user analytics dashboard
- Admin panel: user management, job monitoring, retry failed jobs
- Docker local stack + production deployment behind Traefik

**Deliberately out (post‑MVP — not missing work):**

- Payments, subscriptions, usage quotas
- Direct publishing to TikTok / YouTube / Instagram
- Email notifications (so `/forgot-password` is a UI stub)
- Team workspaces / multi‑seat
- Custom caption templates / brand kits, bulk export, scheduling
