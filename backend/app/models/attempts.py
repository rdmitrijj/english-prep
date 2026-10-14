"""What the candidate did: attempts → attempt_sections → responses; plus the spaced-repetition queue."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import AttemptMode, AttemptStatus, Skill, SubmitReason, str_enum

Band = Numeric(2, 1, asdecimal=False)


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mode: Mapped[AttemptMode] = mapped_column(str_enum(AttemptMode))
    test_id: Mapped[int | None] = mapped_column(ForeignKey("tests.id"))  # NULL for practice/trainer
    status: Mapped[AttemptStatus] = mapped_column(str_enum(AttemptStatus), default=AttemptStatus.in_progress)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overall_band: Mapped[float | None] = mapped_column(Band)
    overall_is_estimate: Mapped[bool] = mapped_column(Boolean, default=False)
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    sections: Mapped[list["AttemptSection"]] = relationship(back_populates="attempt", order_by="AttemptSection.id")


class AttemptSection(Base):
    __tablename__ = "attempt_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), index=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"))  # NULL for a practice session
    skill: Mapped[Skill] = mapped_column(str_enum(Skill))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # NULL = untimed
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submit_reason: Mapped[SubmitReason | None] = mapped_column(str_enum(SubmitReason))
    raw_score: Mapped[int | None] = mapped_column(SmallInteger)
    band: Mapped[float | None] = mapped_column(Band)
    band_table_id: Mapped[int | None] = mapped_column(ForeignKey("band_tables.id"))
    ui_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # highlights, notes, current question

    attempt: Mapped[Attempt] = relationship(back_populates="sections")


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("attempt_section_id", "question_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_section_id: Mapped[int] = mapped_column(ForeignKey("attempt_sections.id", ondelete="CASCADE"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    answer: Mapped[Any] = mapped_column(JSONB, nullable=True)  # string, or list of letters
    is_correct: Mapped[bool | None]
    error_class: Mapped[str | None] = mapped_column(String(40))
    time_ms: Mapped[int] = mapped_column(Integer, default=0)
    change_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    first_answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ReviewItem(Base):
    """Leitner spaced-repetition queue (PLAN §4.5)."""

    __tablename__ = "review_items"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    box: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1–5
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_result: Mapped[bool | None]
