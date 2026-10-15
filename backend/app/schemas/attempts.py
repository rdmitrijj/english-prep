"""Exam payloads. Built from Question/Group/Passage only: answer keys, explanations and evidence
have no field here, so they can never reach a candidate during a test."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AttemptMode, AttemptStatus, QType, Skill, SubmitReason


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OptionOut(Orm):
    letter: str
    text: str


class QuestionOut(Orm):
    id: int
    number: int
    prompt: str
    options: list[OptionOut] | None


class GroupOut(Orm):
    id: int
    qtype: QType
    instructions: str
    max_words: int | None
    options: list[OptionOut] | None
    layout: dict[str, Any] | None
    pick: int  # >1: one checkbox list shared by `pick` question numbers
    questions: list[QuestionOut]


class ParagraphOut(Orm):
    label: str
    text: str


class PassageOut(Orm):
    title: str
    paragraphs: list[ParagraphOut]
    glossary: dict[str, str]


class AudioOut(Orm):
    url: str
    duration_ms: int


class SegmentOut(BaseModel):
    speaker: str
    start_ms: int
    end_ms: int
    text: str


class PartOut(Orm):
    number: int
    passage: PassageOut | None
    audio: AudioOut | None = None
    transcript: list[SegmentOut] | None = None  # practice only: in a mock the transcript would give answers away
    groups: list[GroupOut]


class ResponseOut(Orm):
    question_id: int
    answer: Any
    flagged: bool


class FeedbackOut(BaseModel):
    """Practice only, and only for groups already checked: the key, why it is right, and where in the text."""

    question_id: int
    group_id: int
    number: int
    answer: Any
    accepted: list[str]
    is_correct: bool
    error_class: str | None
    explanation: dict[str, Any]  # {correct, distractors: [{option, why_wrong}]}
    evidence: dict[str, Any]  # {paragraph, quote}


class SectionOut(Orm):
    id: int
    skill: Skill
    duration_s: int | None  # already scaled by EXAM_TIME_SCALE
    started_at: datetime | None
    deadline_at: datetime | None
    submitted_at: datetime | None
    submit_reason: SubmitReason | None
    ui_state: dict[str, Any]
    responses: list[ResponseOut]
    parts: list[PartOut] | None  # only once the section has started
    feedback: list[FeedbackOut] = []  # practice: checked groups only


class AttemptOut(BaseModel):
    id: int
    mode: AttemptMode
    status: AttemptStatus
    test_title: str
    server_now: datetime  # lets the client correct for its own clock drift
    sections: list[SectionOut]


class AttemptSummary(BaseModel):
    id: int
    mode: AttemptMode
    status: AttemptStatus
    test_title: str
    skills: list[Skill]
    started_at: datetime
    bands: list[float | None]


class AttemptCreate(BaseModel):
    mode: Literal[AttemptMode.section_mock]  # ponytail: full_mock arrives in M8, practice in M4
    test_id: int
    skill: Skill


Answer = Annotated[str, Field(max_length=200)] | Annotated[list[Annotated[str, Field(max_length=10)]], Field(max_length=10)] | None


class ResponseIn(BaseModel):
    question_id: int
    answer: Answer
    flagged: bool = False
    time_ms: int = Field(0, ge=0)  # time spent on this question since the last save


class SaveIn(BaseModel):
    responses: list[ResponseIn] = Field(max_length=100)
    ui_state: dict[str, Any] | None = None


class ReportOut(BaseModel):
    id: int
    test_title: str
    mode: AttemptMode
    finished_at: datetime
    overall_band: float | None
    report: dict[str, Any]


class TestSectionOut(Orm):
    skill: Skill
    duration_s: int | None


class TestOut(Orm):
    id: int
    title: str
    sections: list[TestSectionOut]


class SaveOut(BaseModel):
    server_now: datetime
    deadline_at: datetime | None


class PracticeGroup(BaseModel):
    group_id: int
    qtype: QType
    topic: str
    topic_label: str
    level: Literal["easy", "medium", "hard"]
    questions: int
    seen: bool


class PracticeCreate(BaseModel):
    skill: Literal[Skill.reading, Skill.listening]
    qtype: QType | None = None
    topic: str | None = None
    level: Literal["easy", "medium", "hard"] | None = None


class CheckIn(BaseModel):
    group_id: int
