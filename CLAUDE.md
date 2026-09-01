# CLAUDE.md - Segmently Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** Segmently
**Description:** A SaaS tool that automatically turns long-form videos into short,
self-contained ~1-minute vertical clips ready to post as Shorts, Reels, or TikToks.
**Target User:** Solo content creators and streamers (YouTubers, podcasters, Twitch
streamers, educators); secondarily social/content managers at small brands/agencies and
coaches/course creators/B2B marketers.

**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + Vite + TypeScript
- Database: PostgreSQL + SQLAlchemy
- Auth: JWT (email/password) + Google OAuth 2.0
- UI: Tailwind CSS + shadcn/ui + Framer Motion
- Media: S3-compatible object storage, background worker + queue (Redis), Whisper STT,
  Claude for segment detection, FFmpeg for rendering
- Payments: none (deferred to post-MVP)

---

## Project Structure

```
segmently/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── refresh_token.py
│   │   │   ├── project.py
│   │   │   ├── transcript.py
│   │   │   ├── processing_job.py
│   │   │   ├── clip.py
│   │   │   └── clip_caption.py
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── projects.py
│   │   │   ├── clips.py
│   │   │   ├── dashboard.py
│   │   │   └── admin.py
│   │   ├── services/
│   │   │   ├── storage.py
│   │   │   ├── transcription.py
│   │   │   ├── segmentation.py
│   │   │   └── rendering.py
│   │   ├── workers/          # background jobs: download, transcribe, segment, render
│   │   └── auth/
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── context/
│   │   └── types/
│   └── package.json
├── .claude/
│   └── commands/
├── skills/
├── agents/
└── PRPs/
```

---

## Code Standards

### Python (Backend)
```python
# ALWAYS use type hints
def get_project(db: Session, project_id: int) -> Project:
    pass

# ALWAYS add docstrings for public functions
def create_clip(db: Session, data: ClipCreate) -> Clip:
    """
    Create a new clip record.

    Args:
        db: Database session
        data: Clip creation data

    Returns:
        Created Clip object
    """
    pass

# Async endpoints
@router.get("/projects/{id}")
async def get_project(id: int, db: Session = Depends(get_db)):
    pass
```

### TypeScript (Frontend)
```typescript
// ALWAYS define interfaces for props and data - NO any types
interface Clip {
  id: number;
  projectId: number;
  title: string;
  startSeconds: number;
  endSeconds: number;
  score: number;
  status: "queued" | "rendering" | "ready" | "failed";
}

const fetchClip = async (id: number): Promise<Clip> => {
  // ...
};
```

---

## Forbidden Patterns

### Backend
- Never use `print()` - use the `logging` module
- Never store passwords in plain text - use bcrypt
- Never hardcode secrets - use environment variables
- Never use `SELECT *` - specify columns
- Never skip input validation (use Pydantic schemas)
- Never run transcription, segmentation, or rendering inside a request handler - enqueue a job
- Never expose raw storage URLs - always issue signed, expiring URLs

### Frontend
- Never use the `any` type
- Never leave `console.log` in production code
- Never skip error handling in async operations
- Never use inline styles - use Tailwind / shadcn components

---

## Module-Specific Rules

### Projects / Uploads
- Every Project has a `user_id`; users can only access their own projects
- Valid `status` values: pending, downloading, transcribing, segmenting, rendering, completed, failed
- URL imports must guard against SSRF (reject private / internal address ranges)
- Uploads must validate MIME type and size before storing; reject non-video content
- Deleting a Project must delete its Transcript, ProcessingJobs, Clips, and all stored media

### Clips
- Every Clip belongs to a Project (and by extension a user)
- Default `aspect_ratio` is "9:16"; target duration ~60s
- Valid `status` values: queued, rendering, ready, failed
- `score` is 0-100; always store a `score_reason` string alongside it
- Editing caption text or trim points sets the clip back to `queued` and requires a re-render

### Admin Panel
- All `/api/v1/admin/*` endpoints require `is_admin`; return 403 otherwise
- Admin routes must not be reachable in the frontend for non-admin users

---

## API Conventions

- All endpoints prefixed with `/api/v1/`
- Use plural nouns for resources: `/projects`, `/clips`
- Return appropriate HTTP status codes:
  - 200 Success, 201 Created, 202 Accepted (job enqueued)
  - 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict
  - 422 Unprocessable Entity (validation)
- Long-running actions return 202 with a job/status reference; clients poll project/job status

---

## Authentication

### JWT Configuration
- Access token expires: 30 minutes
- Refresh token expires: 7 days
- Algorithm: HS256
- Refresh rotates the token and revokes the old one

### OAuth Providers
- Google OAuth 2.0 enabled
- Always verify the `state` parameter for CSRF protection
- On first Google login, create the user with `oauth_provider="google"` and `is_verified=True`

---

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/segmently

# Auth
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback

# Object storage (S3-compatible)
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

## Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Worker (background jobs - requires FFmpeg on PATH)
cd backend
python -m app.workers.run

# Frontend
cd frontend
npm install
npm run dev

# Docker (Postgres, Redis, MinIO, api, worker, web)
docker-compose up -d

# Tests
pytest backend/tests -v
cd frontend && npm test

# Linting / type-checking
ruff check backend/
cd frontend && npm run lint && npm run type-check
```

---

## Validation

```bash
ruff check backend/ && pytest
npm run lint && npm run type-check
docker-compose build
```

---

## Commit Message Format

```
feat(clips): add caption editor
fix(projects): handle failed URL download
refactor(workers): extract rendering service
test(auth): add Google OAuth callback tests
docs: update README
```

---

## Skills Reference

| Task | Skill to Read |
|------|---------------|
| Database models | skills/DATABASE.md |
| API + Auth | skills/BACKEND.md |
| React + UI | skills/FRONTEND.md |
| Testing | skills/TESTING.md |
| Deployment | skills/DEPLOYMENT.md |

---

## Agent Coordination

For complex tasks, the ORCHESTRATOR coordinates:
- DATABASE-AGENT -> Backend models + migrations
- BACKEND-AGENT -> API development + media pipeline / workers
- FRONTEND-AGENT -> UI components + pages
- TEST-AGENT -> Testing
- REVIEW-AGENT -> Security and code review
- DEVOPS-AGENT -> Docker, worker image, queue, CI/CD

Read agent definitions in the `/agents/` folder.
