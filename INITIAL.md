# INITIAL.md - Segmently Product Definition

> Segmently is a SaaS tool that automatically turns long-form videos into short, self-contained clips of about one minute, ready to post as Shorts, Reels, or TikToks.

---

## PRODUCT

### Name
Segmently

### Description
Segmently ingests a long-form video (10 minutes to several hours) via file upload or a
pasted URL (YouTube / public video link), transcribes it, and uses AI to detect the most
compelling self-contained moments. It renders each moment as a vertical 9:16 clip of
roughly one minute with burned-in captions, ranks the clips, and lets the user preview
and download them as MP4 files. No video-editing skill required.

### Target User
**Primary:** Solo content creators and streamers - YouTubers, podcasters, Twitch
streamers, and educators - who record long videos and want a steady stream of vertical
short-form clips without learning a video editor or hiring one.

**Secondary:**
- Social/content managers at small brands and agencies repurposing webinars, interviews,
  and long marketing videos into clips for multiple platforms.
- Coaches, course creators, and B2B marketers using short clips as top-of-funnel content
  to drive traffic to long videos or products.

**Common thread:** a backlog of long video content, pressure to post short-form daily
across several platforms, and limited time, editing skill, or budget to do it manually.

### Type
- [x] SaaS (Software as a Service)

---

## TECH STACK

### Backend
- [x] FastAPI + Python 3.11+

### Frontend
- [x] React + Vite + TypeScript

### Database
- [x] PostgreSQL + SQLAlchemy

### Authentication
- [x] Email/Password + Google OAuth 2.0

### UI Framework
- [x] Tailwind CSS + shadcn/ui (+ Framer Motion for transitions)

### Payments
- [ ] None for MVP (subscription/billing deferred to post-MVP)

### Media / AI Pipeline
- [x] Object storage for source videos and rendered clips (S3-compatible)
- [x] Background worker queue for transcription + clip rendering (long-running jobs)
- [x] Speech-to-text for transcription (e.g. Whisper)
- [x] LLM for segment detection / virality ranking (Claude)
- [x] FFmpeg for cropping, reframing, caption burn-in, encoding

---

## MODULES

### Module 1: Authentication (Required)

**Description:** User authentication and authorization.

**Models:**
- User: id, email, hashed_password, full_name, is_active, is_verified, is_admin, oauth_provider, oauth_sub, created_at, updated_at
- RefreshToken: id, user_id, token, expires_at, revoked, created_at

**API Endpoints:**
- POST /api/v1/auth/register - Create new account
- POST /api/v1/auth/login - Login with email/password
- POST /api/v1/auth/refresh - Refresh access token
- POST /api/v1/auth/logout - Revoke refresh token
- GET /api/v1/auth/me - Get current user profile
- PUT /api/v1/auth/me - Update profile
- GET /api/v1/auth/google/login - Begin Google OAuth flow
- GET /api/v1/auth/google/callback - Google OAuth callback (verifies state for CSRF)

**Frontend Pages:**
- /login - Login page
- /register - Registration page
- /forgot-password - Forgot password page (email delivery deferred; UI stubbed)
- /profile - User profile page (protected)

---

### Module 2: Projects / Uploads

**Description:** Manages source videos. A user creates a Project by uploading a video file
or pasting a URL. Segmently fetches/stores the video, runs transcription, and tracks
processing status through to clip generation.

**Models:**
- Project: id, user_id, title, source_type (upload | url), source_url, storage_key, duration_seconds, file_size_bytes, status (pending | downloading | transcribing | segmenting | rendering | completed | failed), error_message, thumbnail_key, created_at, updated_at
- Transcript: id, project_id, language, full_text, segments (JSON: [{start, end, text}]), created_at
- ProcessingJob: id, project_id, job_type (download | transcribe | segment | render), status, progress_pct, started_at, finished_at, error_message

**API Endpoints:**
- GET /api/v1/projects - List current user's projects (paginated)
- POST /api/v1/projects - Create project from a URL
- POST /api/v1/projects/upload - Create project via direct file upload (multipart)
- GET /api/v1/projects/{id} - Project detail incl. status and job progress
- DELETE /api/v1/projects/{id} - Delete project, clips, and stored media
- POST /api/v1/projects/{id}/reprocess - Re-run the pipeline
- GET /api/v1/projects/{id}/transcript - Get transcript

**Frontend Pages:**
- /projects - List of projects with status badges
- /projects/new - Upload file or paste URL
- /projects/:id - Project detail: source info, processing progress, generated clips

---

### Module 3: Clips

**Description:** AI-generated ~1-minute vertical clips derived from a Project. Users
preview clips, tweak caption text and crop/reframe, see a virality/interest score, and
download the final MP4.

**Models:**
- Clip: id, project_id, user_id, title, start_seconds, end_seconds, duration_seconds, aspect_ratio (default 9:16), status (queued | rendering | ready | failed), score (0-100), score_reason, storage_key, thumbnail_key, caption_style (JSON), created_at, updated_at
- ClipCaption: id, clip_id, segments (JSON: [{start, end, text}]), edited (bool)

**API Endpoints:**
- GET /api/v1/projects/{project_id}/clips - List clips for a project
- GET /api/v1/clips/{id} - Clip detail
- PUT /api/v1/clips/{id} - Update title, trim points, caption text, caption style
- POST /api/v1/clips/{id}/rerender - Re-render after edits
- GET /api/v1/clips/{id}/download - Signed download URL for the MP4
- DELETE /api/v1/clips/{id} - Delete a clip

**Frontend Pages:**
- /clips - All clips across projects (filter by project, sort by score)
- /clips/:id - Clip preview player, caption editor, crop/reframe control, download button

---

### Module 4: Analytics Dashboard

**Description:** Overview and usage metrics for the signed-in user.

**API Endpoints:**
- GET /api/v1/dashboard/summary - Totals: minutes uploaded, projects, clips generated, clips downloaded
- GET /api/v1/dashboard/usage?range=30d - Time series: minutes processed and clips generated per day
- GET /api/v1/dashboard/top-clips - Highest-scoring recent clips

**Frontend Pages:**
- /dashboard - Widgets: minutes used, clips generated, recent projects, top clips, usage charts
- /settings - User settings and preferences

---

### Module 5: Admin Panel

**Description:** Admin-only management interface (is_admin users only).

**API Endpoints:**
- GET /api/v1/admin/users - List all users (search, paginate)
- PUT /api/v1/admin/users/{id} - Update user status (active, admin, verified)
- GET /api/v1/admin/stats - Platform stats: users, projects, clips, storage used
- GET /api/v1/admin/jobs - Monitor processing jobs (status, failures, queue depth)
- POST /api/v1/admin/jobs/{id}/retry - Retry a failed job

**Frontend Pages:**
- /admin - Admin dashboard (protected, admin only)
- /admin/users - User management
- /admin/jobs - Processing job monitor

---

## MVP SCOPE

### Must Have (MVP)
- [x] User registration and login (email/password + Google OAuth)
- [x] Upload a video file OR paste a YouTube/URL link to create a Project
- [x] Auto-transcribe the video and AI-detect the best ~1-minute segments
- [x] Generate vertical (9:16) clips with burned-in captions
- [x] Preview clips in-app and download as MP4

### Nice to Have (Post-MVP)
- [ ] Direct publishing to TikTok / YouTube Shorts / Instagram Reels
- [ ] Subscription plans, billing, and usage quotas
- [ ] Email notifications ("your clips are ready", quota warnings)
- [ ] Team workspaces / multi-seat
- [ ] Custom caption templates and brand kits
- [ ] Bulk export / scheduling

---

## ACCEPTANCE CRITERIA

### Authentication
- [ ] User can register with email/password
- [ ] User can login with email/password
- [ ] User can login with Google OAuth (state parameter verified for CSRF)
- [ ] JWT access + refresh tokens work correctly; refresh rotates tokens
- [ ] Protected routes redirect unauthenticated users to /login

### Projects / Uploads
- [ ] User can create a project from a file upload and from a URL
- [ ] Project status transitions are visible and update as the pipeline runs
- [ ] A failed job surfaces an error message and can be reprocessed
- [ ] Deleting a project removes its clips and stored media
- [ ] Users can only see and act on their own projects

### Clips
- [ ] The pipeline produces multiple ~1-minute 9:16 clips per completed project
- [ ] Each clip has burned-in captions and an interest/virality score
- [ ] User can edit caption text and trim points and re-render
- [ ] User can download a finished clip as an MP4 via a signed URL

### Analytics Dashboard
- [ ] Dashboard shows minutes processed, projects, and clips generated
- [ ] Usage chart reflects the selected time range

### Admin Panel
- [ ] Non-admin users get 403 on all /admin endpoints and cannot see admin routes
- [ ] Admin can list users and toggle active/admin/verified
- [ ] Admin can monitor jobs and retry failed ones

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully

---

## SPECIAL REQUIREMENTS

### Security
- [x] Rate limiting on auth endpoints
- [x] Input validation on all endpoints (Pydantic)
- [x] SQL injection prevention (parameterized queries / ORM)
- [x] XSS prevention
- [x] CSRF protection on the OAuth flow (state parameter)
- [x] Signed, expiring URLs for media download; no public bucket listing
- [x] File-type and size validation on uploads; reject non-video content
- [x] URL-import SSRF protection (block internal/private address ranges)

### Media Pipeline
- [x] Transcription, segmentation, and rendering run as background jobs, not in request handlers
- [x] Long uploads use resumable / chunked upload or direct-to-storage signed uploads
- [x] Idempotent, retryable jobs with progress reporting
- [x] Storage cleanup on project/clip deletion

### Integrations
- [x] Object storage (S3-compatible) for source video and rendered clips
- [x] Background worker + queue (e.g. Celery/RQ/Arq + Redis)
- [x] Speech-to-text service (Whisper or hosted equivalent)
- [x] LLM (Claude) for segment detection and scoring
- [x] FFmpeg available in the worker image
- [ ] Email service (deferred to post-MVP)
- [ ] Payments (deferred to post-MVP)

---

## AGENTS

> These 6 agents will build Segmently in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | User, RefreshToken, Project, Transcript, ProcessingJob, Clip, ClipCaption |
| BACKEND-AGENT | Builds API endpoints, services, and the media pipeline | All modules' backends + worker jobs |
| FRONTEND-AGENT | Creates UI pages and components | All modules' frontends |
| DEVOPS-AGENT | Sets up Docker, worker image (FFmpeg), queue, CI/CD, environments | Infrastructure |
| TEST-AGENT | Writes unit and integration tests | All code |
| REVIEW-AGENT | Security and code quality audit | All code |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/segmently-prp.md
```
