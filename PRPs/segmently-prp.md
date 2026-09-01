# PRP: Segmently

> Implementation blueprint for parallel agent execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | Segmently |
| **Type** | SaaS (AI video repurposing) |
| **Version** | 1.0 |
| **Created** | 2026-08-29 |
| **Complexity** | High (async media pipeline + AI + storage) |

---

## PRODUCT OVERVIEW

**Description:** Segmently ingests a long-form video (10 min - several hours) via file
upload or a pasted URL, transcribes it, and uses an LLM to detect the most compelling
self-contained moments. Each moment is rendered as a vertical 9:16 clip of roughly one
minute with burned-in captions, ranked by an interest/virality score, and made available
for in-app preview and MP4 download.

**Value Proposition:** Creators with a backlog of long videos get a steady stream of
post-ready short-form clips in minutes - no video editor to learn, no editor to hire.

**MVP Scope:**
- [ ] User registration and login (email/password + Google OAuth)
- [ ] Create a Project from a file upload OR a pasted YouTube/URL link
- [ ] Auto-transcribe the video and AI-detect the best ~1-minute segments
- [ ] Generate vertical (9:16) clips with burned-in captions and a score
- [ ] Preview clips in-app and download as MP4

**Out of scope (post-MVP):** direct social publishing, subscriptions/billing/quotas,
email notifications, team workspaces, custom caption templates, scheduling.

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy + Alembic | skills/DATABASE.md |
| Auth | JWT + bcrypt + Google OAuth 2.0 | skills/BACKEND.md |
| UI | Tailwind CSS + shadcn/ui + Framer Motion | skills/FRONTEND.md |
| Queue / Worker | Redis + Arq (or Celery/RQ) | skills/BACKEND.md |
| Storage | S3-compatible object storage (MinIO in dev) | skills/DEPLOYMENT.md |
| Transcription | Whisper (local or hosted) | skills/BACKEND.md |
| Segmentation / scoring | Claude (`claude-sonnet-5`) | skills/BACKEND.md |
| Media rendering | FFmpeg | skills/DEPLOYMENT.md |
| Testing | pytest + React Testing Library | skills/TESTING.md |
| Deployment | Docker + docker-compose + GitHub Actions | skills/DEPLOYMENT.md |

---

## DATABASE MODELS

### User
- id, email (unique), hashed_password (nullable for OAuth), full_name, is_active,
  is_verified, is_admin, oauth_provider (nullable), oauth_sub (nullable), created_at, updated_at
- Relationships: projects[], clips[], refresh_tokens[]

### RefreshToken
- id, user_id (FK User), token (unique), expires_at, revoked (bool), created_at

### Project
- id, user_id (FK User), title, source_type (enum: upload | url), source_url (nullable),
  storage_key (nullable), duration_seconds (nullable), file_size_bytes (nullable),
  status (enum: pending | downloading | transcribing | segmenting | rendering | completed | failed),
  error_message (nullable), thumbnail_key (nullable), created_at, updated_at
- Relationships: transcript (1:1), jobs[], clips[]

### Transcript
- id, project_id (FK Project, unique), language, full_text,
  segments (JSON: [{start, end, text}]), created_at

### ProcessingJob
- id, project_id (FK Project), job_type (enum: download | transcribe | segment | render),
  status (enum: queued | running | completed | failed), progress_pct (int 0-100),
  started_at (nullable), finished_at (nullable), error_message (nullable), created_at

### Clip
- id, project_id (FK Project), user_id (FK User), title, start_seconds, end_seconds,
  duration_seconds, aspect_ratio (default "9:16"),
  status (enum: queued | rendering | ready | failed), score (int 0-100),
  score_reason (text), storage_key (nullable), thumbnail_key (nullable),
  caption_style (JSON), created_at, updated_at
- Relationships: caption (1:1)

### ClipCaption
- id, clip_id (FK Clip, unique), segments (JSON: [{start, end, text}]), edited (bool)

---

## MODULES

### Module 1: Authentication
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/register | Create account |
| POST | /api/v1/auth/login | Get access + refresh tokens |
| POST | /api/v1/auth/refresh | Rotate refresh token |
| POST | /api/v1/auth/logout | Revoke refresh token |
| GET | /api/v1/auth/me | Current user profile |
| PUT | /api/v1/auth/me | Update profile |
| GET | /api/v1/auth/google/login | Begin Google OAuth |
| GET | /api/v1/auth/google/callback | OAuth callback (verify `state`) |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /login | LoginPage | LoginForm, GoogleButton |
| /register | RegisterPage | RegisterForm |
| /forgot-password | ForgotPasswordPage | ForgotPasswordForm (UI stub) |
| /profile | ProfilePage | ProfileForm |

---

### Module 2: Projects / Uploads
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/projects | List current user's projects (paginated) |
| POST | /api/v1/projects | Create project from a URL (returns 202) |
| POST | /api/v1/projects/upload | Create project via file upload / signed upload (202) |
| GET | /api/v1/projects/{id} | Project detail incl. status + job progress |
| DELETE | /api/v1/projects/{id} | Delete project, clips, and stored media |
| POST | /api/v1/projects/{id}/reprocess | Re-run the pipeline |
| GET | /api/v1/projects/{id}/transcript | Get transcript |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /projects | ProjectsListPage | ProjectCard, StatusBadge, EmptyState |
| /projects/new | NewProjectPage | UploadDropzone, UrlImportForm |
| /projects/:id | ProjectDetailPage | PipelineProgress, ClipGrid, TranscriptPanel |

**Pipeline (worker jobs):** download -> transcribe -> segment -> render (one ProcessingJob
row per stage; status/progress polled by frontend).

---

### Module 3: Clips
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/projects/{project_id}/clips | List clips for a project |
| GET | /api/v1/clips/{id} | Clip detail |
| PUT | /api/v1/clips/{id} | Update title, trim points, caption text, caption style |
| POST | /api/v1/clips/{id}/rerender | Re-render after edits (202) |
| GET | /api/v1/clips/{id}/download | Signed, expiring MP4 download URL |
| DELETE | /api/v1/clips/{id} | Delete a clip + media |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /clips | ClipsLibraryPage | ClipCard, ScoreBadge, ProjectFilter, SortControl |
| /clips/:id | ClipDetailPage | VerticalVideoPlayer, CaptionEditor, ReframeControl, DownloadButton |

---

### Module 4: Analytics Dashboard
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/dashboard/summary | Totals: minutes uploaded, projects, clips, downloads |
| GET | /api/v1/dashboard/usage?range=30d | Time series: minutes processed + clips/day |
| GET | /api/v1/dashboard/top-clips | Highest-scoring recent clips |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /dashboard | DashboardPage | StatCard, UsageChart, RecentProjects, TopClips |
| /settings | SettingsPage | SettingsForm |

---

### Module 5: Admin Panel
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/admin/users | List all users (search, paginate) |
| PUT | /api/v1/admin/users/{id} | Update is_active / is_admin / is_verified |
| GET | /api/v1/admin/stats | Platform stats: users, projects, clips, storage used |
| GET | /api/v1/admin/jobs | Monitor processing jobs (status, failures, queue depth) |
| POST | /api/v1/admin/jobs/{id}/retry | Retry a failed job |

All `/api/v1/admin/*` require `is_admin` -> 403 otherwise.

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /admin | AdminDashboardPage | AdminStatCard |
| /admin/users | AdminUsersPage | UserTable, UserEditModal |
| /admin/jobs | AdminJobsPage | JobTable, RetryButton |

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: All models, relationships, enums, Alembic migration, `database.py`, seed admin user
- BACKEND-AGENT: `main.py`, `config.py`, router skeletons, dependency wiring, health endpoint, queue/worker bootstrap
- FRONTEND-AGENT: Vite + TS setup, Tailwind + shadcn init, folder structure, API client, auth context, routing shell, base components
- DEVOPS-AGENT: `docker-compose.yml` (postgres, redis, minio, api, worker, web), worker Dockerfile with FFmpeg, `.env.example`, GitHub Actions CI

**Validation Gate 1:** `pip install -r requirements.txt`, `alembic upgrade head`, `npm install`, `docker-compose config`

**Phase 2: Modules (backend + frontend parallel per module)**
1. Auth Module: JWT + bcrypt + Google OAuth endpoints; Login/Register/Profile pages
2. Projects / Uploads: upload + URL create, status/detail endpoints, worker `download` + `transcribe` jobs; list/new/detail pages
3. Clips: list/detail/update/rerender/download endpoints, worker `segment` (Claude) + `render` (FFmpeg) jobs; library + clip editor pages
4. Analytics Dashboard: summary/usage/top-clips endpoints; dashboard + settings pages
5. Admin Panel: admin endpoints with `is_admin` guard; admin users + jobs pages

**Validation Gate 2:** `ruff check backend/`, `mypy backend/app` (or `pyright`), `npm run lint`, `npm run type-check`

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest (unit + integration, mocked Whisper/Claude/FFmpeg/storage) + RTL tests, 80%+ coverage
- REVIEW-AGENT: security audit (authz on every resource, SSRF on URL import, upload validation, signed URLs, OAuth state), performance review (N+1 queries, job idempotency)
- RESEARCH-AGENT: validate FFmpeg reframe/caption approach and Whisper/Claude usage against current best practices

**Final Validation:** full test suite, `docker-compose up -d`, `curl localhost:8000/health`, end-to-end smoke: create project from URL -> clips ready -> download.

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config` |
| 2 | `ruff check backend/`, `npm run type-check` |
| 3 | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/segmently

# Auth
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Object storage (S3-compatible / MinIO in dev)
STORAGE_ENDPOINT_URL=http://localhost:9000
STORAGE_BUCKET=segmently-media
STORAGE_ACCESS_KEY=xxx
STORAGE_SECRET_KEY=xxx

# Worker / queue
REDIS_URL=redis://localhost:6379/0

# AI pipeline
WHISPER_MODEL=base
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-5

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## KEY RISKS / NOTES

- **Long-running work must never block request handlers** - every pipeline stage is an
  enqueued, idempotent, retryable job with progress reporting.
- **SSRF on URL import** - resolve and reject private/link-local/internal addresses before fetching.
- **Upload safety** - validate MIME/type + size; use signed direct-to-storage or chunked upload for large files.
- **Media access** - only signed, expiring URLs; buckets are private; clean up storage on delete.
- **AI cost/latency** - cap source duration for MVP; cache transcripts; batch segment analysis.
- **FFmpeg in worker image only** - keep it out of the API image.

---

## NEXT STEP

Execute with parallel agents:

```bash
/execute-prp PRPs/segmently-prp.md
```
