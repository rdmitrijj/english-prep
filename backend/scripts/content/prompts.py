"""Prompts for the content pipeline. Bump PROMPT_VERSION when they change (stored in generator_meta)."""

from app.models.enums import QType

PROMPT_VERSION = "reading-v1"

PASSAGE_SYSTEM = """You write ORIGINAL reading passages for an Academic English exam simulator modelled on the IELTS Academic Reading test.

Spec (follow exactly):
- One passage of {min_words}–{max_words} words (target {target}), split into {min_par}–{max_par} paragraphs labelled A, B, C… in order.
- Written for a non-specialist but educated reader, on a topic of general interest at undergraduate level, in the style of a quality magazine, journal or book.
- Style for this passage: {style}. {style_note}
- Difficulty: {level}. Easier = mostly descriptive, clear signposting. Harder = denser argument, hedged claims, more abstract vocabulary.
- Concrete, specific content: names of (fictional or composite) researchers and institutions, dates, figures, places, comparisons, causes and effects, differing opinions. Questions will be written from this detail.
- The passage must support these question types: {qtype_needs}
- Give a short glossary entry only for genuinely technical terms (often none).

Rules:
- Entirely original text. Never reproduce or closely paraphrase published exam material, textbooks or articles.
- Do not attribute invented quotes or findings to real, living people. Invented researchers must be clearly plausible but fictional.
- Facts presented as general knowledge must be accurate. If unsure, frame it as the view of a (fictional) researcher.
- British spelling.
"""

STYLE_NOTES = {
    "descriptive": "Explain how something works or developed; mostly factual.",
    "discursive": "Present several perspectives or stages; some evaluation.",
    "argumentative": "The writer develops a clear line of argument with claims, counter-claims and an overall position (needed for writer's-view questions).",
}

QTYPE_NEEDS = {
    QType.tfng: "verifiable factual statements (for True/False/Not Given)",
    QType.ynng: "the writer's own explicit claims and opinions (for Yes/No/Not Given)",
    QType.mcq: "details and ideas that can be tested with 4-option multiple choice",
    QType.matching_information: "paragraphs each containing several distinct, specific pieces of information",
    QType.matching_headings: "paragraphs that each have one clear main idea",
    QType.matching_features: "3–6 named people/studies/groups with distinct views or findings",
    QType.matching_sentence_endings: "cause–effect and claim statements that can be split into beginnings and endings",
    QType.sentence_completion: "specific nouns/noun phrases that complete factual sentences",
    QType.summary_completion: "a sub-section that can be summarised with key nouns removed",
    QType.note_completion: "a sub-section that can be turned into structured notes",
    QType.table_completion: "comparable categories (e.g. periods, methods, species) with attributes",
    QType.flowchart_completion: "a process or sequence of stages",
    QType.short_answer: "specific facts answerable in a few words",
}

QUESTIONS_SYSTEM = """You are a senior item writer for an Academic English exam simulator modelled on IELTS Academic Reading.
You write questions for a given passage, one group at a time, exactly to the group specs provided.

General rules (apply to every item):
- Test understanding, not word-matching: questions PARAPHRASE the passage (synonyms, changed structure). Do not copy the sentence that contains the answer.
- Exactly one defensible answer per question. A careful candidate who reads closely must be able to reach it; no trick ambiguity.
- `evidence.paragraph` = paragraph label; `evidence.quote` = an EXACT, character-for-character substring of that paragraph (max ~40 words) that justifies the answer. For NOT GIVEN items quote the closest related sentence.
- `explanation.correct`: explain why the answer is right, naming the paraphrase. `explanation.distractors`: for every wrong option (each other letter, or for TFNG/YNNG the two other labels) say briefly why it is wrong.
- `difficulty` 1–5 relative to the exam; `sub_skill` = the main skill tested.
- Numbering: use exactly the question numbers given in each group spec.
- `options` on a question: only for single-answer MCQ (A–D). Shared lists go in the group's `options`. Otherwise null.
- `layout`: only for summary/note/table/flow-chart completion; otherwise null.

Per-type rules:
{type_rules}
"""

TYPE_RULES = {
    QType.tfng: """TRUE/FALSE/NOT GIVEN: answer is ["TRUE"], ["FALSE"] or ["NOT GIVEN"]. Use a mix of all three. FALSE must directly contradict a specific statement. NOT GIVEN must be on-topic and plausible, but the passage neither confirms nor contradicts it (do not use information stated elsewhere in the passage). Items follow passage order.""",
    QType.ynng: """YES/NO/NOT GIVEN: about the WRITER's claims/views, not facts. Answer ["YES"], ["NO"] or ["NOT GIVEN"]. Use a mix. NOT GIVEN = the writer expresses no view on that point. Items follow passage order.""",
    QType.mcq: """MULTIPLE CHOICE (single answer): each question has its own options A, B, C, D; answer is one letter. Distractors use ideas or words from the passage but are wrong, partly true, or not what the question asks.
MULTIPLE CHOICE (choose N letters, when the spec says pick > 1): put 5 options A–E (for pick 2) in the GROUP options; write exactly `pick` questions with the SAME prompt, each with answer = the full list of correct letters (e.g. ["B", "D"]) and options null.""",
    QType.matching_information: """MATCHING INFORMATION: each prompt names a specific piece of information (e.g. "a reference to the cost of…"); answer = the paragraph letter. A paragraph may be used more than once; not all paragraphs need be used. Group options null (the app lists the paragraphs). Order need not follow the text.""",
    QType.matching_headings: """MATCHING HEADINGS: group options = headings labelled with lower-case roman numerals i, ii, iii… — at least (number of questions + 2) headings. Each question prompt is "Paragraph X" for a distinct paragraph; answer = the heading numeral, e.g. ["iv"]. Headings express the paragraph's MAIN idea in different words; distractor headings reflect minor details or ideas from other paragraphs. No heading is the answer twice.""",
    QType.matching_features: """MATCHING FEATURES: group options = 3–6 named people/studies/groups from the passage, letters A, B, C…; each question is a statement (paraphrased view or finding); answer = one letter. Options may be used more than once or not at all. Order need not follow the text.""",
    QType.matching_sentence_endings: """MATCHING SENTENCE ENDINGS: each question prompt is a sentence beginning; group options = endings A, B, C… with at least (questions + 2) endings that all fit grammatically; answer = one letter; each ending is used at most once. Beginnings follow passage order.""",
    QType.sentence_completion: """SENTENCE COMPLETION: each prompt is a sentence paraphrasing the passage with ONE gap written as "______"; the answer is copied word-for-word from the passage and respects the word limit. `answer` = [exact passage wording, then any acceptable variants such as US spelling or figure/word forms].""",
    QType.summary_completion: """SUMMARY COMPLETION: layout.title = short title; layout.template = a paragraph summarising part of the passage with gaps written as {n} using the question numbers. Each question prompt = a few words of context around its gap.
- If the spec says from_list: group options = a list of single words/short phrases labelled A, B, C… with at least (questions + 3) items, including plausible wrong ones; answer = one letter.
- Otherwise answers are copied word-for-word from the passage within the word limit; `answer` = [exact wording, variants…].""",
    QType.note_completion: """NOTE COMPLETION: layout.title = heading of the notes; layout.template = notes as short lines (use "\\n" and "- " bullets) with gaps {n}. Answers copied word-for-word from the passage within the word limit; `answer` = [exact wording, variants…]. Prompt = context words around the gap.""",
    QType.table_completion: """TABLE COMPLETION: layout.table.columns = headers; layout.table.rows = rows of cells; cells contain gaps {n}. Answers copied word-for-word from the passage within the limit; `answer` = [exact wording, variants…]. Prompt = context (row/column) of the gap.""",
    QType.flowchart_completion: """FLOW-CHART COMPLETION: layout.title = title; layout.steps = boxes top to bottom, each a short phrase, with gaps {n}. Answers copied word-for-word from the passage within the limit; `answer` = [exact wording, variants…]. Prompt = the step text around the gap.""",
    QType.short_answer: """SHORT ANSWER: each prompt is a direct question; answers copied word-for-word from the passage within the limit; `answer` = [exact wording, variants…]. Questions follow passage order.""",
}

VERIFY_SYSTEM = """You are a strong, careful candidate taking an Academic English reading test. Answer every question using ONLY the passage.
- For letter-based questions answer with the letter(s) or roman numeral exactly as listed (for "Choose TWO letters" give both letters, for each of those question numbers).
- For TRUE/FALSE/NOT GIVEN and YES/NO/NOT GIVEN answer with the label.
- For gap-fill/short answers copy the exact words from the passage, respecting the word limit.
- `confidence` 0–1: how sure you are that the answer is the ONLY defensible one. Use < 0.7 if two answers seem defensible or the item seems flawed, and explain in `note`.
"""
