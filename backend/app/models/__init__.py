"""Importing this package registers every table on Base.metadata (needed by Alembic)."""

from app.models import attempts, content, speaking, usage, users, writing  # noqa: F401
