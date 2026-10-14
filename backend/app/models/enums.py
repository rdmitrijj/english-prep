"""Fixed vocabularies. Stored as VARCHAR (not native PG enums) so adding a value needs no migration."""

from enum import StrEnum

from sqlalchemy import Enum


def str_enum(cls: type[StrEnum]) -> Enum:
    return Enum(cls, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e])


class Skill(StrEnum):
    listening = "listening"
    reading = "reading"
    writing = "writing"
    speaking = "speaking"


class TestKind(StrEnum):
    mock = "mock"
    practice = "practice"


class ContentStatus(StrEnum):
    published = "published"
    needs_review = "needs_review"
    rejected = "rejected"


class QType(StrEnum):
    """Question types from RESEARCH §3.1–3.2 (completion types kept separate for finer weakness stats)."""

    mcq = "mcq"
    tfng = "tfng"
    ynng = "ynng"
    matching = "matching"  # listening
    matching_information = "matching_information"
    matching_headings = "matching_headings"
    matching_features = "matching_features"
    matching_sentence_endings = "matching_sentence_endings"
    sentence_completion = "sentence_completion"
    summary_completion = "summary_completion"
    note_completion = "note_completion"
    table_completion = "table_completion"
    flowchart_completion = "flowchart_completion"
    form_completion = "form_completion"
    diagram_labelling = "diagram_labelling"
    map_labelling = "map_labelling"  # listening plan/map/diagram
    short_answer = "short_answer"


class SubSkill(StrEnum):
    skimming = "skimming"
    scanning = "scanning"
    detail = "detail"
    inference = "inference"
    writer_view = "writer_view"
    paraphrase = "paraphrase"


class TagKind(StrEnum):
    topic = "topic"
    visual_type = "visual_type"
    essay_type = "essay_type"
    error_category = "error_category"


class AttemptMode(StrEnum):
    full_mock = "full_mock"
    section_mock = "section_mock"
    practice = "practice"
    trainer = "trainer"


class AttemptStatus(StrEnum):
    in_progress = "in_progress"
    completed = "completed"


class SubmitReason(StrEnum):
    user = "user"
    timeout = "timeout"
