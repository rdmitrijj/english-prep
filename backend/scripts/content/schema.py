"""Content file format (content/tests/<slug>.json).

`*Draft` models are what the LLM fills in (OpenAI strict schemas: no dicts, no defaults).
The `C*` models extend them with fields the pipeline adds, and are what `seed` loads into the DB.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import ContentStatus, QType, Skill, SubSkill, TestKind


class Option(BaseModel):
    letter: str  # "A", "B"… or "i", "ii"… for headings
    text: str


class Evidence(BaseModel):
    paragraph: str  # Reading: paragraph label, e.g. "C". Listening: script line index, filled in by the pipeline
    quote: str  # exact substring of that paragraph / line


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


Accent = Literal["en-GB", "en-AU", "en-NZ", "en-US", "en-CA"]


class Speaker(BaseModel):
    id: str  # used by lines, e.g. "narrator", "woman", "tutor"
    role: str  # who they are, e.g. "hotel receptionist"
    accent: Accent
    gender: Literal["female", "male"]


class Line(BaseModel):
    speaker: str  # a Speaker.id
    text: str
    pause_after_s: float = 0.0  # extra silence after the line: reading time before questions, review time
    answer_s: int | None = None  # Speaking: the candidate answers this line, for at most this long


class CScript(BaseModel):
    """A Listening recording, narration included ("You will hear… First, you have some time to look at questions 1 to 5")."""

    speakers: list[Speaker]
    lines: list[Line]


class Segment(BaseModel):
    speaker: str
    accent: str
    start_ms: int
    end_ms: int
    text: str
    answer_s: int | None = None  # Speaking: copied from the script line


class CAudio(BaseModel):
    """Written by `scripts.content.audio render`; one segment per script line, with exact timestamps."""

    url: str  # /media/audio/<slug>-p<n>.mp3
    duration_ms: int
    segments: list[Segment]
    tts_provider: str
    voices: dict[str, str]  # speaker id → voice id


VisualType = Literal["line", "bar", "pie", "table", "mixed", "process", "map"]
EssayType = Literal["opinion", "discussion", "advantages_disadvantages", "problem_solution", "two_part"]


class Series(BaseModel):
    name: str
    values: list[float]


class Chart(BaseModel):
    """One chart or table, drawn from these numbers by `scripts.content.visuals`; the examiner gets the same numbers."""

    type: Literal["line", "bar", "pie", "table"]
    title: str
    unit: str  # e.g. "%", "millions of tonnes": the y-axis label, or the table's unit line
    categories: list[str]  # x-axis points (line), bar groups (bar), slices (pie), row labels (table)
    series: list[Series]  # one line / bar colour / pie / table column each; len(values) == len(categories)


class CVisual(BaseModel):
    type: VisualType
    charts: list[Chart] = []  # line/bar/pie/table: one; mixed: two
    description: str | None = None  # process/map: every stage or feature in words, the examiner's source of truth
    url: str | None = None  # /media/visuals/<file>.svg: rendered for charts, hand-drawn for process/map


class CWriting(BaseModel):
    task_number: Literal[1, 2]
    prompt: str  # only the task's own text; the fixed rubric lines come from spec.writing_rubric
    essay_type: EssayType | None = None  # Task 2
    visual: CVisual | None = None  # Task 1


class CueCard(BaseModel):
    """Speaking Part 2. Shown as: task, "You should say:", the bullets, then the final line."""

    task: str  # "Describe a time when you helped someone."
    bullets: list[str]  # "who you helped", "why they needed help"…
    final: str  # "and explain how you felt about helping them."


class CPart(BaseModel):
    number: int
    context: str
    topic: str  # topic tag slug, e.g. "biology-ecology"
    passage: CPassage | None = None
    script: CScript | None = None  # listening; speaking (the examiner's lines)
    cue_card: CueCard | None = None  # speaking Part 2
    audio: CAudio | None = None  # listening, after rendering
    writing: CWriting | None = None
    groups: list[CGroup] = []  # none for writing


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
