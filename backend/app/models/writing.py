from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, CreatedAt


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_section_id: Mapped[int] = mapped_column(ForeignKey("attempt_sections.id", ondelete="CASCADE"))
    writing_task_id: Mapped[int] = mapped_column(ForeignKey("writing_tasks.id"))
    text: Mapped[str] = mapped_column(Text, default="")
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    time_ms: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WritingEvaluation(CreatedAt, Base):
    __tablename__ = "writing_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("writing_submissions.id", ondelete="CASCADE"), index=True)
    run_no: Mapped[int] = mapped_column(SmallInteger)  # 1–3 (PLAN §5 double-run rule)
    model: Mapped[str] = mapped_column(String(60))
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB)
    task_band: Mapped[float] = mapped_column(Numeric(3, 2, asdecimal=False))  # unrounded mean of criteria
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    weakness_tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB)
    inconsistent: Mapped[bool] = mapped_column(Boolean, default=False)
