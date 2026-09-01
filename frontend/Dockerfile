# ---------------------------------------------------------------------------
# Segmently frontend image: build the Vite/React app, then serve the static
# bundle with nginx (SPA fallback). Runs as a non-root user.
# ---------------------------------------------------------------------------

# ----- Stage 1: build the static bundle -----------------------------------
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
# Use the lockfile when present (reproducible); fall back to `npm install`
# so the image builds before a package-lock.json has been generated.
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY . .

# VITE_API_URL is baked in at build time; override with
#   docker compose build --build-arg VITE_API_URL=...
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ----- Stage 2: serve with nginx ----------------------------------------
FROM nginxinc/nginx-unprivileged:1.27-alpine AS serve

# nginx-unprivileged already runs as UID 101 (user "nginx") and listens on 8080.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
