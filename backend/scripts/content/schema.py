"""Content file format (content/tests/<slug>.json).

`*Draft` models are what the LLM fills in (OpenAI strict schemas: no dicts, no defaults).
The `C*` models extend them with fields the pipeline adds, and are what `seed` loads into the DB.
"""

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ContentStatus, QType, Skill, SubSkill, TestKind


class Option(BaseModel):
    letter: str  # "A", "B"… or "i", "ii"… for headings
    text: str


class Evidence(BaseModel):
    paragraph: str  # paragraph label, e.g. "C"
    quote: str  # exact substring of that paragraph


class DistractorNote(BaseModel):
    option: str  # a letter, or e.g. "FALSE"
    why_wrong: str


class Explanation(BaseModel):
    correct: str
    distractors: list[DistractorNote]


class TableLayout(BaseModel):
    columns: list[str]
    rows: list[list[str]]  # cells may contain gap markers like {7}


class Layout(BaseModel):
    """Shared visual for completion groups. Gap markers are {question_number}."""

    title: str | None
    template: str | None  # summary / notes text
    table: TableLayout | None
    steps: list[str] | None  # flow-chart boxes, top to bottom


class Paragraph(BaseModel):
    label: str
    text: str


class GlossaryEntry(BaseModel):
    term: str
    definition: str


# ---------- what the LLM writes ----------

class PassageDraft(BaseModel):
    title: str
    paragraphs: list[Paragraph]
    glossary: list[GlossaryEntry]


class QuestionDraft(BaseModel):
    number: int
    prompt: str
    options: list[Option] | None  # per-question options (single-answer MCQ only)
    answer: list[str]  # accepted variants (completion) or the correct letter(s)
    difficulty: int = Field(ge=1, le=5)
    sub_skill: SubSkill
    explanation: Explanation
    evidence: Evidence


class GroupDraft(BaseModel):
    options: list[Option] | None  # shared options (matching, headings, word lists, multi-answer MCQ)
    layout: Layout | None
    questions: list[QuestionDraft]


class GroupsDraft(BaseModel):
    groups: list[GroupDraft]


class VerifierAnswer(BaseModel):
    number: int
    answer: list[str]
    confidence: float = Field(ge=0, le=1)
    note: str


class VerifierAnswers(BaseModel):
    answers: list[VerifierAnswer]


# ---------- what is stored in content/ ----------

class Review(BaseModel):
    reason: str
    verifier_answer: list[str] | None = None
    confidence: float | None = None


class CQuestion(QuestionDraft):
    review: Review | None = None


class CGroup(GroupDraft):
    qtype: QType
    instructions: str
    max_words: int | None = None
    allow_number: bool = False
    pick: int = 1  # letters to choose (multi-answer MCQ)
    questions: list[CQuestion]


class CPassage(PassageDraft):
    pass


class CPart(BaseModel):
    number: int
    context: str
    topic: str  # topic tag slug, e.g. "biology-ecology"
    passage: CPassage | None = None
    groups: list[CGroup]


class CSection(BaseModel):
    skill: Skill
    duration_s: int | None
    parts: list[CPart]


class CTest(BaseModel):
    slug: str
    kind: TestKind
    title: str
    status: ContentStatus
    generator_meta: dict[str, Any] = {}
    check_errors: list[str] = []
    sections: list[CSection]

    def questions(self):
        for section in self.sections:
            for part in section.parts:
                for group in part.groups:
                    yield from group.questions
