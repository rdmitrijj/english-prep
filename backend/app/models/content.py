"""Test content: tests → sections → parts → (passage | audio | writing task) + question groups → questions."""

from typing import Any

from sqlalchemy import Boolean, Column, ForeignKey, SmallInteger, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, CreatedAt
from app.models.enums import ContentStatus, QType, Skill, SubSkill, TagKind, TestKind, str_enum


class Test(CreatedAt, Base):
    __tablename__ = "tests"
    __test__ = False  # tell pytest this is not a test class

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    kind: Mapped[TestKind] = mapped_column(str_enum(TestKind))
    status: Mapped[ContentStatus] = mapped_column(str_enum(ContentStatus))
    title: Mapped[str] = mapped_column(String(200))
    generator_meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    sections: Mapped[list["Section"]] = relationship(back_populates="test", order_by="Section.order")


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("test_id", "skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id", ondelete="CASCADE"))
    skill: Mapped[Skill] = mapped_column(str_enum(Skill))
    order: Mapped[int] = mapped_column(SmallInteger)
    duration_s: Mapped[int | None]  # NULL for listening: audio length + 120 s review

    test: Mapped[Test] = relationship(back_populates="sections")
    parts: Mapped[list["Part"]] = relationship(back_populates="section", order_by="Part.number")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("kind", "slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[TagKind] = mapped_column(str_enum(TagKind))
    slug: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120))


class Part(Base):
    __tablename__ = "parts"
    __table_args__ = (UniqueConstraint("section_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(SmallInteger)  # L 1–4, R 1–3, W 1–2
    context: Mapped[str | None] = mapped_column(String(40))  # e.g. social_dialogue, academic_lecture
    topic_tag_id: Mapped[int | None] = mapped_column(ForeignKey("tags.id"))

    section: Mapped[Section] = relationship(back_populates="parts")
    question_groups: Mapped[list["QuestionGroup"]] = relationship(
        back_populates="part", order_by="QuestionGroup.order"
    )


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    paragraphs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # [{label: "A", text}]
    word_count: Mapped[int]
    glossary: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)


class AudioAsset(Base):
    __tablename__ = "audio_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), unique=True)
    url: Mapped[str] = mapped_column(String(300))
    duration_ms: Mapped[int]
    segments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # [{speaker, accent, start_ms, end_ms, text}]
    tts_provider: Mapped[str] = mapped_column(String(40))
    voices: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)


writing_task_tags = Table(
    "writing_task_tags",
    Base.metadata,
    Column("writing_task_id", ForeignKey("writing_tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class WritingTask(Base):
    __tablename__ = "writing_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"), unique=True)
    task_number: Mapped[int] = mapped_column(SmallInteger)
    prompt: Mapped[str] = mapped_column(Text)
    visual_url: Mapped[str | None] = mapped_column(String(300))
    visual_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # source data, given to the evaluator

    tags: Mapped[list[Tag]] = relationship(secondary=writing_task_tags)


speaking_prompt_tags = Table(
    "speaking_prompt_tags",
    Base.metadata,
    Column("speaking_prompt_id", ForeignKey("speaking_prompts.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class SpeakingPrompt(Base):
    __tablename__ = "speaking_prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    part_number: Mapped[int] = mapped_column(SmallInteger)
    topic: Mapped[str] = mapped_column(String(120))
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)  # P1 questions | P2 cue card | P3 questions

    tags: Mapped[list[Tag]] = relationship(secondary=speaking_prompt_tags)


class QuestionGroup(Base):
    __tablename__ = "question_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    part_id: Mapped[int] = mapped_column(ForeignKey("parts.id", ondelete="CASCADE"))
    order: Mapped[int] = mapped_column(SmallInteger)
    qtype: Mapped[QType] = mapped_column(str_enum(QType))
    instructions: Mapped[str] = mapped_column(Text)
    max_words: Mapped[int | None] = mapped_column(SmallInteger)  # NULL = not a gap-fill
    allow_number: Mapped[bool] = mapped_column(Boolean, default=False)
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)  # [{letter, text}]
    layout: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # summary/table/flow-chart template, map SVG

    part: Mapped[Part] = relationship(back_populates="question_groups")
    questions: Mapped[list["Question"]] = relationship(back_populates="group", order_by="Question.number")


question_tags = Table(
    "question_tags",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("question_groups.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(SmallInteger)  # 1–40 within its section
    prompt: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(SmallInteger)  # 1–5
    sub_skill: Mapped[SubSkill | None] = mapped_column(str_enum(SubSkill))
    explanation: Mapped[dict[str, Any]] = mapped_column(JSONB)  # {correct, distractors: {letter: why}}
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB)  # paragraph label/segment index + char span

    group: Mapped[QuestionGroup] = relationship(back_populates="questions")
    tags: Mapped[list[Tag]] = relationship(secondary=question_tags)


class AnswerKey(Base):
    """Kept apart from Question so exam payloads can never leak answers by accident."""

    __tablename__ = "answer_keys"

    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    accepted: Mapped[list[str]] = mapped_column(JSONB)  # text variants, or letters
    pick: Mapped[int] = mapped_column(SmallInteger, default=1)  # letters to choose (multi-answer MCQ)


class BandTable(CreatedAt, Base):
    __tablename__ = "band_tables"
    __table_args__ = (UniqueConstraint("skill", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    skill: Mapped[str] = mapped_column(String(32))  # listening | reading_academic
    version: Mapped[str] = mapped_column(String(40))
    rows: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # [{min_raw, max_raw, band, estimated?}]
    source: Mapped[str] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
