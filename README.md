# MicroSaaS Template

> **Clone. Define. Build.** Full-stack SaaS in minutes.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/manojkanur/MicroSaaS-Template-Private.git my-saas
cd my-saas

# 2. Define your product
# Edit INITIAL.md with your product details

# 3. Generate blueprint
/generate-prp INITIAL.md

# 4. Build with parallel agents
/execute-prp PRPs/[name]-prp.md
```

---

## What You Get

- FastAPI backend with JWT + Google OAuth
- React frontend with modern UI (Framer Motion)
- PostgreSQL database with migrations
- Docker + CI/CD ready
- 80%+ test coverage

---

## How It Works

```
INITIAL.md → /generate-prp → PRP blueprint → /execute-prp → Full App

Phase 1 (Parallel):
├─ DATABASE-AGENT  → Models + migrations
├─ BACKEND-AGENT   → API structure
├─ FRONTEND-AGENT  → React setup
└─ DEVOPS-AGENT    → Docker + CI

Phase 2 (Per Module):
├─ Backend endpoints
└─ Frontend pages

Phase 3 (Parallel):
├─ TEST-AGENT      → 80%+ coverage
└─ REVIEW-AGENT    → Security audit
```

---

## Files

| File | Purpose |
|------|---------|
| `INITIAL.md` | Define your product |
| `CLAUDE.md` | Project rules |
| `skills/*.md` | Code patterns (5 files) |
| `agents/*.md` | Agent definitions |
| `.claude/commands/` | Custom commands |

---

## Skills (5 files)

| Skill | Contains |
|-------|----------|
| `BACKEND.md` | FastAPI + JWT + OAuth + Errors |
| `FRONTEND.md` | React + UI Kit + API integration |
| `DATABASE.md` | SQLAlchemy + Alembic |
| `TESTING.md` | pytest + Vitest |
| `DEPLOYMENT.md` | Docker + GitHub Actions |

---

## Commands

| Command | Description |
|---------|-------------|
| `/setup-project` | Interactive wizard |
| `/generate-prp` | Create implementation blueprint |
| `/execute-prp` | Build with parallel agents |

---

## Tech Stack

- **Backend:** FastAPI + Python 3.11+
- **Frontend:** React + TypeScript + Vite
- **Database:** PostgreSQL + SQLAlchemy
- **Auth:** JWT + Google OAuth
- **UI:** Chakra UI or Tailwind + Framer Motion
- **Deploy:** Docker + GitHub Actions

---

## Example

```bash
# Define an invoice SaaS in INITIAL.md:
# - Module: Invoices (CRUD)
# - Module: Clients (CRUD)
# - Module: Dashboard

/generate-prp INITIAL.md
# Creates PRPs/invoice-saas-prp.md

/execute-prp PRPs/invoice-saas-prp.md
# 4 agents build in parallel
# ~20-30 minutes for complete app
```

---

## Output Structure

```
my-saas/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   └── auth/
│   ├── alembic/
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       └── services/
├── docker-compose.yml
└── .github/workflows/
```

---

## Run Locally

```bash
# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker
docker-compose up -d
```

---

## Running with Docker

The full stack (API, media worker, Postgres, Redis, MinIO, web) runs with Docker Compose.

### Prerequisites

- Docker Engine 24+ and the Docker Compose v2 plugin (`docker compose`)

### First run

```bash
# 1. Create your env file
cp .env.example .env        # defaults already target the compose network

# 2. Build and start everything
docker compose up -d --build

# 3. Create the object-storage bucket (one-shot; also runs automatically)
docker compose run --rm createbuckets

# 4. Apply database migrations
docker compose exec api alembic upgrade head
```

### Services & ports

| Service        | URL / Port                        | Notes                                            |
|----------------|-----------------------------------|--------------------------------------------------|
| `web`          | http://localhost:3000             | React SPA served by nginx                        |
| `api`          | http://localhost:8000             | FastAPI; health check at `/health`               |
| `worker`       | -                                 | `arq` media pipeline (shares the backend image, includes FFmpeg) |
| `db`           | localhost:5432                    | PostgreSQL 16, database `segmently`, volume `pgdata` |
| `redis`        | localhost:6379                    | Queue broker, volume `redisdata`                 |
| `minio`        | http://localhost:9000 (API), http://localhost:9001 (console) | S3-compatible storage, volume `miniodata` |
| `createbuckets`| -                                 | One-shot: creates `STORAGE_BUCKET` in MinIO then exits |

The `api` and `worker` services are built from the **same** `backend/Dockerfile`.
FFmpeg is installed in that image because the worker renders clips with it.

### Development (hot reload)

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

This override bind-mounts `backend/` and `frontend/`, runs `uvicorn --reload`,
runs the worker with `arq --watch`, and replaces the nginx `web` container with
the Vite dev server on http://localhost:3000.

### Common commands

```bash
docker compose logs -f api worker      # tail logs
docker compose exec api bash           # shell into the API container
docker compose exec api alembic upgrade head
docker compose down                    # stop
docker compose down -v                 # stop and wipe volumes (db/redis/minio data)
```

> Note: the `worker` service runs `arq app.workers.settings.WorkerSettings`.
> That module is added by the Phase 2 backend work; until it exists the worker
> container will restart-loop. Comment the service out or switch it to the
> documented placeholder command in `docker-compose.yml` if you need a quiet start.
