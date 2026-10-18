# Two targets: `dev` (docker-compose.yml) and `prod` (the last stage, so a plain `docker build`, and Render, build it).
FROM python:3.13-slim AS backend-base
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv
# The virtualenv lives outside the source dir so the dev bind-mount doesn't hide it.
ENV UV_PROJECT_ENVIRONMENT=/venv UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH=/venv/bin:$PATH
WORKDIR /srv/backend
COPY backend/pyproject.toml backend/uv.lock ./

FROM backend-base AS dev
# ffmpeg encodes Listening audio to MP3 when building content (scripts/content/audio.py)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN uv sync --frozen
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

FROM node:24-alpine AS frontend-build
WORKDIR /srv/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# One service serves /api, /media and the built frontend. Media is baked in (Render's disk is ephemeral).
FROM backend-base AS prod
RUN uv sync --frozen --no-dev
COPY backend/alembic.ini ./
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY content/media /srv/content/media
COPY --from=frontend-build /srv/frontend/dist /srv/frontend/dist
RUN useradd --system app
USER app
# Render sets $PORT. Migrations run at start because Render's pre-deploy command is paid-only.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
