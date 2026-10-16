"""Exam blueprint from RESEARCH §2–3: question-type mixes, word limits and exact rubric wording.

Rubric text is produced HERE (not by the LLM) so the wording is always exact.
"""

from dataclasses import dataclass, field

from app.models.enums import QType

READING_WORDS = (700, 1000)  # per passage; target 750–900, total 2,150–2,750 (RESEARCH §2.2)
READING_TOTAL_WORDS = (2150, 2750)

# Reading topic areas (RESEARCH §8, unofficial)
READING_TOPICS = {
    "biology-ecology": "Biology and ecology",
    "history-archaeology": "History and archaeology",
    "psychology": "Psychology and behaviour",
    "linguistics-education": "Language and education",
    "technology-engineering": "Technology and engineering",
    "earth-science-climate": "Earth science and climate",
    "health-medicine": "Health and medicine",
    "business-economics": "Business and economics",
    "architecture-urban": "Architecture and urban planning",
    "agriculture-food": "Agriculture and food",
    "arts-culture": "Arts and culture",
    "astronomy-physics": "Astronomy and physics",
}

# Listening contexts (RESEARCH §2.1 / §8): Parts 1–2 everyday life, Parts 3–4 education and training.
LISTENING_TOPICS = {
    "accommodation": "Accommodation and housing",
    "travel-transport": "Travel and transport",
    "local-services": "Local services and facilities",
    "leisure-events": "Leisure, clubs and events",
    "work-jobs": "Work and jobs",
    "study-courses": "Study, courses and assignments",
    "health-fitness": "Health and fitness",
}
# Writing themes (RESEARCH §8, unofficial): Task 2 essays, and Task 1 data subjects.
WRITING_TOPICS = {
    "education": "Education",
    "technology": "Technology",
    "environment": "Environment",
    "health": "Health",
    "work-economy": "Work and the economy",
    "government-law": "Government, law and crime",
    "society-family": "Society and family",
    "media-culture": "Media, advertising and culture",
    "cities-transport": "Cities and transport",
    "travel-tourism": "Travel and tourism",
    "energy-resources": "Energy and resources",
}
TOPIC_LABELS = READING_TOPICS | LISTENING_TOPICS | WRITING_TOPICS
VISUAL_LABELS = {"line": "Line graph", "bar": "Bar chart", "pie": "Pie chart", "table": "Table",
                 "mixed": "Two charts", "process": "Process diagram", "map": "Maps"}
ESSAY_LABELS = {"opinion": "Opinion (agree or disagree)", "discussion": "Discuss both views",
                "advantages_disadvantages": "Advantages and disadvantages", "problem_solution": "Problem and solution",
                "two_part": "Two-part question"}


def writing_rubric(task_number: int, prompt: str) -> str:
    """The exact CD-test wording around a task's own text (RESEARCH §2.3); paragraphs separated by blank lines."""
    if task_number == 1:
        lines = ["You should spend about 20 minutes on this task.", prompt,
                 "Summarise the information by selecting and reporting the main features, and make comparisons where relevant.",
                 "Write at least 150 words."]
    else:
        lines = ["You should spend about 40 minutes on this task.", "Write about the following topic:", prompt,
                 "Give reasons for your answer and include any relevant examples from your own knowledge or experience.",
                 "Write at least 250 words."]
    return "\n\n".join(lines)
LISTENING_CONTEXTS = ("social_dialogue", "social_monologue", "academic_discussion", "academic_lecture")
SPEECH_WPS = 2.6  # words per second of natural TTS speech, for duration estimates before rendering
LINE_GAP_S = 0.4  # silence between consecutive lines
LISTENING_AUDIO_MIN = (26, 32)  # a whole mock recording; + 2 min review = the official 30–34 min (RESEARCH §2.1)

TEXT_TYPES = {
    QType.sentence_completion, QType.summary_completion, QType.note_completion, QType.form_completion,
    QType.table_completion, QType.flowchart_completion, QType.short_answer,
}  # answers are words copied from the passage or recording (unless `from_list`)
ORDERED_TYPES = TEXT_TYPES | {QType.tfng, QType.ynng}  # these follow the order of the text


@dataclass
class GroupSpec:
    qtype: QType
    count: int
    max_words: int | None = None
    allow_number: bool = False
    from_list: bool = False  # summary completion choosing from a word list
    pick: int = 1  # multi-answer MCQ: "Choose TWO letters"


@dataclass
class PassageSpec:
    groups: list[GroupSpec]
    level: str  # "easier" | "medium" | "harder" — difficulty rises across the test
    style: str  # descriptive | discursive | argumentative
    topic: str | None = None  # READING_TOPICS key; None → chosen by the pipeline

    @property
    def count(self) -> int:
        return sum(g.count for g in self.groups)


G = GroupSpec
MOCK_READING: dict[str, list[PassageSpec]] = {
    "mock-01": [
        PassageSpec([G(QType.tfng, 6), G(QType.note_completion, 7, max_words=1)], "easier", "descriptive"),
        PassageSpec([G(QType.matching_headings, 6), G(QType.matching_features, 3),
                     G(QType.sentence_completion, 4, max_words=2)], "medium", "discursive"),
        PassageSpec([G(QType.mcq, 5), G(QType.ynng, 5), G(QType.matching_sentence_endings, 4)], "harder", "argumentative"),
    ],
    "mock-02": [
        PassageSpec([G(QType.matching_information, 4), G(QType.table_completion, 5, max_words=2, allow_number=True),
                     G(QType.tfng, 4)], "easier", "descriptive"),
        PassageSpec([G(QType.matching_headings, 7), G(QType.mcq, 2, pick=2), G(QType.short_answer, 4, max_words=3)],
                    "medium", "discursive"),
        PassageSpec([G(QType.ynng, 6), G(QType.summary_completion, 5, from_list=True), G(QType.mcq, 3)],
                    "harder", "argumentative"),
    ],
    "mock-03": [
        PassageSpec([G(QType.tfng, 7), G(QType.flowchart_completion, 6, max_words=2)], "easier", "descriptive"),
        PassageSpec([G(QType.matching_information, 5), G(QType.matching_features, 4),
                     G(QType.summary_completion, 4, max_words=1)], "medium", "discursive"),
        PassageSpec([G(QType.matching_headings, 6), G(QType.ynng, 4), G(QType.mcq, 4)], "harder", "argumentative"),
    ],
    "mock-04": [
        PassageSpec([G(QType.note_completion, 6, max_words=2, allow_number=True), G(QType.tfng, 7)], "easier", "descriptive"),
        PassageSpec([G(QType.matching_headings, 5), G(QType.sentence_completion, 4, max_words=3),
                     G(QType.mcq, 4)], "medium", "discursive"),
        PassageSpec([G(QType.matching_sentence_endings, 5), G(QType.ynng, 5), G(QType.mcq, 2, pick=2),
                     G(QType.short_answer, 2, max_words=2)], "harder", "argumentative"),
    ],
}

@dataclass
class RecordingSpec:
    groups: list[GroupSpec]
    context: str  # one of LISTENING_CONTEXTS
    level: str

    @property
    def count(self) -> int:
        return sum(g.count for g in self.groups)


MOCK_LISTENING: dict[str, list[RecordingSpec]] = {
    "mock-01": [
        RecordingSpec([G(QType.form_completion, 10, max_words=1, allow_number=True)], "social_dialogue", "easier"),
        RecordingSpec([G(QType.mcq, 4), G(QType.matching, 6)], "social_monologue", "easier"),
        RecordingSpec([G(QType.mcq, 2, pick=2), G(QType.mcq, 3), G(QType.matching, 5)], "academic_discussion", "medium"),
        RecordingSpec([G(QType.note_completion, 10, max_words=1)], "academic_lecture", "harder"),
    ],
}

# ---------- rubric wording ----------

_LIMITS = {
    (1, False): "ONE WORD ONLY",
    (1, True): "ONE WORD AND/OR A NUMBER",
    (2, False): "NO MORE THAN TWO WORDS",
    (2, True): "NO MORE THAN TWO WORDS AND/OR A NUMBER",
    (3, False): "NO MORE THAN THREE WORDS",
    (3, True): "NO MORE THAN THREE WORDS AND/OR A NUMBER",
}
_NUMBERS = {2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE", 6: "SIX", 7: "SEVEN", 8: "EIGHT"}


def letters(n: int) -> list[str]:
    return [chr(ord("A") + i) for i in range(n)]


def roman(n: int) -> list[str]:
    return "i ii iii iv v vi vii viii ix x xi xii".split()[:n]


def listening_instructions(g: GroupSpec, first: int, last: int, n_options: int) -> str:
    """Listening rubric: limits say "Write …", MCQ has three options (RESEARCH §3.1, §3.3)."""
    last_opt = letters(n_options)[-1] if n_options else ""
    limit = f"Write {_LIMITS[(g.max_words, g.allow_number)]} for each answer." if g.max_words else ""
    noun = {QType.form_completion: "form", QType.note_completion: "notes", QType.table_completion: "table",
            QType.flowchart_completion: "flow-chart", QType.sentence_completion: "sentences",
            QType.summary_completion: "summary"}
    match g.qtype:
        case QType.mcq if g.pick > 1:
            return f"Choose {_NUMBERS[g.pick]} letters, A–{last_opt}."
        case QType.mcq:
            return "Choose the correct letter, A, B or C."
        case QType.matching:
            return (f"Choose {_NUMBERS.get(last - first + 1, last - first + 1)} answers from the box and move them "
                    f"into the gaps next to Questions {first}–{last}.")
        case QType.short_answer:
            return f"Answer the questions below.\n{limit}"
        case t if t in noun:
            return f"Complete the {noun[t]} below.\n{limit}"
    raise ValueError(f"no listening rubric for {g.qtype}")


def instructions(g: GroupSpec, first: int, last: int, passage_no: int, n_paragraphs: int, n_options: int) -> str:
    """Exact rubric for a question group (paper wording adapted to the CD interface, RESEARCH §3.3)."""
    rng = f"{first}–{last}"
    last_par = letters(n_paragraphs)[-1]
    last_opt = letters(n_options)[-1] if n_options else ""
    limit = f"Choose {_LIMITS[(g.max_words, g.allow_number)]} from the passage for each answer." if g.max_words else ""
    write = "Write your answers in the gaps."
    match g.qtype:
        case QType.tfng:
            return (f"Do the following statements agree with the information given in Reading Passage {passage_no}?\n"
                    "Choose\nTRUE if the statement agrees with the information\n"
                    "FALSE if the statement contradicts the information\n"
                    "NOT GIVEN if there is no information on this")
        case QType.ynng:
            return (f"Do the following statements agree with the claims of the writer in Reading Passage {passage_no}?\n"
                    "Choose\nYES if the statement agrees with the claims of the writer\n"
                    "NO if the statement contradicts the claims of the writer\n"
                    "NOT GIVEN if it is impossible to say what the writer thinks about this")
        case QType.mcq if g.pick > 1:
            return f"Choose {_NUMBERS[g.pick]} letters, A–{last_opt}."
        case QType.mcq:
            return "Choose the correct letter, A, B, C or D."
        case QType.matching_information:
            return (f"Reading Passage {passage_no} has {n_paragraphs} paragraphs, A–{last_par}.\n"
                    "Which paragraph contains the following information?\nNB You may use any letter more than once.")
        case QType.matching_headings:
            return (f"Reading Passage {passage_no} has {n_paragraphs} paragraphs, A–{last_par}.\n"
                    "Choose the correct heading for each paragraph from the list of headings below.")
        case QType.matching_features:
            return (f"Look at the following statements (Questions {rng}) and the list below.\n"
                    f"Match each statement with the correct option, A–{last_opt}.\nNB You may use any letter more than once.")
        case QType.matching_sentence_endings:
            return f"Complete each sentence with the correct ending, A–{last_opt}, below."
        case QType.summary_completion if g.from_list:
            return f"Complete the summary using the list of words, A–{last_opt}, below."
        case QType.summary_completion:
            return f"Complete the summary below.\n{limit}\n{write}"
        case QType.sentence_completion:
            return f"Complete the sentences below.\n{limit}\n{write}"
        case QType.note_completion:
            return f"Complete the notes below.\n{limit}\n{write}"
        case QType.table_completion:
            return f"Complete the table below.\n{limit}\n{write}"
        case QType.flowchart_completion:
            return f"Complete the flow-chart below.\n{limit}\n{write}"
        case QType.short_answer:
            return f"Answer the questions below.\n{limit}\n{write}"
    raise ValueError(f"no rubric for {g.qtype}")
