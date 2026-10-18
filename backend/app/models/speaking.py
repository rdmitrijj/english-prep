"""Speaking (M10): one recording per answered examiner question, and the examiners' verdicts on the whole interview."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt


class SpeakingAnswer(Base):
    __tablename__ = "speaking_answers"
    __table_args__ = (UniqueConstraint("attempt_section_id", "part_number", "line_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_section_id: Mapped[int] = mapped_column(ForeignKey("attempt_sections.id", ondelete="CASCADE"))
    part_number: Mapped[int] = mapped_column(SmallInteger)
    line_no: Mapped[int] = mapped_column(SmallInteger)  # index of the examiner's line (audio segment) answered
    question: Mapped[str] = mapped_column(Text)  # snapshot of what the examiner said
    # ponytail: audio in Postgres (~0.5 MB per 2 min of Opus; Neon free has 0.5 GB). Move to R2 if it fills up.
    audio: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    mime: Mapped[str] = mapped_column(String(60))
    duration_ms: Mapped[int] = mapped_column(Integer)
    transcript: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # {text, words: [{w, start, end, p}]} (Whisper)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SpeakingEvaluation(CreatedAt, Base):
    __tablename__ = "speaking_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_section_id: Mapped[int] = mapped_column(ForeignKey("attempt_sections.id", ondelete="CASCADE"), index=True)
    run_no: Mapped[int] = mapped_column(SmallInteger)  # 1–3, the same double-run rule as Writing
    model: Mapped[str] = mapped_column(String(60))
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB)
    task_band: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False))  # unrounded mean of the criteria
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    weakness_tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)
    inconsistent: Mapped[bool] = mapped_column(Boolean, default=False)
