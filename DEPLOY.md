# Deploying Segmently to a VPS

Target: a single Hostinger VPS (Ubuntu 22.04/24.04), domain **segmently.online**,
HTTPS via Caddy + Let's Encrypt, everything in Docker Compose.

```
Internet ──▶ Caddy (:443, auto-TLS)
             ├─ segmently.online        → web (SPA)  +  /api/* → api (FastAPI)
             └─ s3.segmently.online     → minio  (signed clip URLs)
                        │
             db · redis · minio · worker   (internal only, no public ports)
```

Files used (all in the repo):
`docker-compose.yml` + `deploy/docker-compose.prod.yml` + `deploy/Caddyfile` +
`deploy/.env.prod` (you create this) + `deploy/segmently.sh` (helper).

---

## 0. What you need before starting

| Thing | Where from |
|---|---|
| VPS **public IP** + SSH access (root or a sudo user) | Hostinger hPanel → VPS |
| VPS specs: **2+ vCPU, 4+ GB RAM, 40+ GB disk** | see "Sizing" below |
| Domain **segmently.online** with DNS you can edit | Hostinger (or wherever it's registered) |
| **OpenAI API key** | you have it |
| **Pexels API key** (for B-roll) | you have it |
| *(optional)* Google OAuth client ID + secret | Google Cloud Console |
| A real **admin email** + you choose strong passwords | — |

### Sizing

Rendering is CPU-bound (FFmpeg). Rough guide per **1-hour source video**:

| VPS | transcribe+segment | render 6 clips | good for |
|---|---|---|---|
| 2 vCPU / 4 GB | ~2 min | ~15–25 min | testing, a few users |
| 4 vCPU / 8 GB | ~2 min | ~6–10 min | small production |
| 8 vCPU / 16 GB | ~2 min | ~4–6 min | comfortable |

Disk: a processed 1-hour video keeps ~600 MB of source + ~150 MB of clips in MinIO.
40 GB ≈ 50 processed videos before you need cleanup or a bigger disk.

---

## 1. DNS

In your DNS provider, add these records (replace `VPS_IP`):

| Type | Name | Value | TTL |
|---|---|---|---|
| A | `@` (segmently.online) | `VPS_IP` | 300 |
| A | `www` | `VPS_IP` | 300 |
| A | `s3` | `VPS_IP` | 300 |

Wait for them to resolve (`dig +short segmently.online` from your laptop should show
`VPS_IP`). Caddy can't get certificates until DNS points at the box.

---

## 2. Prepare the VPS

SSH in, then:

```bash
# --- Docker + compose plugin ---
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"        # log out/in after this

# --- firewall: only SSH + web ---
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw --force enable

# --- swap (important on 4 GB boxes: pip/npm builds need headroom) ---
sudo fallocate -l 4G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Log out and back in so the `docker` group applies.

---

## 3. Get the code

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> segmently      # or scp the folder up
sudo chown -R "$USER":"$USER" segmently
cd segmently
```

If the repo isn't on a git host, from your laptop:
`rsync -av --exclude .git --exclude node_modules --exclude '__pycache__' ./ user@VPS_IP:/opt/segmently/`

---

## 4. Configure `deploy/.env.prod`

```bash
cp deploy/.env.prod.example deploy/.env.prod
# generate secrets:
echo "SECRET_KEY=$(openssl rand -hex 32)"
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
echo "STORAGE_ACCESS_KEY=$(openssl rand -hex 12)"
echo "STORAGE_SECRET_KEY=$(openssl rand -hex 24)"
nano deploy/.env.prod
```

Fill in **every `CHANGE_ME`**, plus:

- `SITE_DOMAIN=segmently.online`, `S3_DOMAIN=s3.segmently.online`
- `ACME_EMAIL=` your email
- `DATABASE_URL` — must contain the **same** password as `POSTGRES_PASSWORD`
- `OPENAI_API_KEY`, `PEXELS_API_KEY`
- `ADMIN_EMAIL` (a real address), `ADMIN_PASSWORD`
- Leave `GOOGLE_*` blank for now (section 7)

`DEBUG=false` is already set — the API **refuses to start** if `SECRET_KEY` /
`ADMIN_PASSWORD` / the DB password are still the shipped defaults, so you can't
accidentally launch insecure.

`deploy/.env.prod` is git-ignored. Keep a copy somewhere safe.

---

## 5. First deploy

```bash
chmod +x deploy/segmently.sh
./deploy/segmently.sh up
```

This builds the images (first build ~5–10 min), starts everything, runs the DB
migration, and seeds the admin user. Caddy fetches TLS certs automatically once
DNS is live (watch with `./deploy/segmently.sh logs caddy`).

Then open **https://segmently.online**, log in with the `ADMIN_EMAIL` /
`ADMIN_PASSWORD` you set, and paste a video URL.

---

## 6. Verify

```bash
./deploy/segmently.sh ps                     # all services "Up"/"healthy"
curl -sf https://segmently.online/health     # {"status":"healthy",...}
curl -sf -o /dev/null -w '%{http_code}\n' https://s3.segmently.online/minio/health/live
./deploy/segmently.sh logs worker            # watch a pipeline run
```

Run one clip end-to-end and confirm it plays + downloads from the app.

---

## 7. Google OAuth (optional)

1. Google Cloud Console → APIs & Services → Credentials → **OAuth client ID** → Web.
2. Authorized redirect URI: `https://segmently.online/api/v1/auth/google/callback`
3. Put the client ID + secret in `deploy/.env.prod`
   (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), keep `GOOGLE_REDIRECT_URI` as-is.
4. `./deploy/segmently.sh update`

Email/password login works without this.

---

## 8. Day-2 operations

```bash
./deploy/segmently.sh update        # git pull + rebuild + migrate (deploy new code)
./deploy/segmently.sh backup        # gzipped pg_dump into ./backups/
./deploy/segmently.sh logs api      # tail one service
./deploy/segmently.sh logs          # tail everything
./deploy/segmently.sh migrate       # run migrations only
docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml \
  --env-file deploy/.env.prod up -d --scale worker=2   # more render throughput
```

**Nightly DB backup** (cron): `crontab -e` →
`0 3 * * * cd /opt/segmently && ./deploy/segmently.sh backup >> /var/log/segmently-backup.log 2>&1`

**MinIO data** lives in the `miniodata` docker volume — snapshot the VPS or
`docker run --rm -v microsaasapp_miniodata:/data -v $PWD/backups:/b alpine tar czf /b/minio-$(date +%F).tgz -C /data .`

**Free disk** when it fills: delete old projects from the app (removes their media),
or prune: `docker system prune -af`.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| Caddy can't get a cert | DNS not resolving yet, or ports 80/443 blocked. `dig +short segmently.online`; `sudo ufw status`. |
| API container restarts / "Insecure default value(s)" | a `CHANGE_ME` is still in `deploy/.env.prod`. |
| Clips play but won't load / 403 | `STORAGE_PUBLIC_ENDPOINT_URL` must be `https://s3.segmently.online` and the `s3` DNS record must exist. |
| Uploads fail on large files | already allowed to 6 GB in the Caddyfile; check `MAX_UPLOAD_BYTES`. |
| Renders very slow / OOM | small VPS. Lower `SEGMENTS_TARGET`, keep `RENDER_MODE=fit` off for talking heads (`RENDER_MODE=crop` is ~3× faster), or resize the VPS. |
| Worker "Timeout connecting to server" once at boot | Redis wasn't ready yet; it self-recovers. |
| Transcription errors | `TRANSCRIPTION_BACKEND=openai` needs a valid `OPENAI_API_KEY`; `=local` needs no key but is much slower. |

---

## 10. Later / nice-to-have

- **Object storage → Cloudflare R2 or Backblaze B2** instead of on-box MinIO
  (set `STORAGE_ENDPOINT_URL` / keys, drop the `minio` service and the `s3` subdomain).
  Cheaper at scale, offloads disk + egress.
- **Email** (password reset, "clips ready") — wire an SMTP provider; currently deferred.
- **Separate render box** — run extra `worker` containers on a second VPS pointed at
  the same Redis + Postgres + storage.
- **Backups off-box** — ship `./backups` to R2/S3 nightly.
