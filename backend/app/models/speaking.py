from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt


class SpeakingSession(Base):
    __tablename__ = "speaking_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_section_id: Mapped[int] = mapped_column(ForeignKey("attempt_sections.id", ondelete="CASCADE"))
    prompt_ids: Mapped[list[int]] = mapped_column(JSONB)
    model: Mapped[str] = mapped_column(String(60))
    transcript: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SpeakingEvaluation(CreatedAt, Base):
    __tablename__ = "speaking_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("speaking_sessions.id", ondelete="CASCADE"), index=True)
    model: Mapped[str] = mapped_column(String(60))
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB)
    band: Mapped[float] = mapped_column(Numeric(2, 1, asdecimal=False))
    pronunciation_is_estimate: Mapped[bool] = mapped_column(Boolean, default=True)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)
