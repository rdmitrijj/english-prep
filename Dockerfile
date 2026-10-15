# Backend image. M9 adds a frontend-build stage and a production target.
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
