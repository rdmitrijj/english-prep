# Brief: writing Reading content for English-prep

You write ORIGINAL Academic Reading passages and questions for an exam simulator modelled on the IELTS Academic
Reading test (computer-delivered). Never reproduce or closely paraphrase published exam material, textbooks or
articles. No invented quotes or findings attributed to real, living people. British spelling. Never put "IELTS"
in titles.

## The rules you follow

- Passage rules: `PASSAGE_SYSTEM` + `STYLE_NOTES` + `QTYPE_NEEDS` in `backend/scripts/content/prompts.py`.
- Item rules: `QUESTIONS_SYSTEM` + `TYPE_RULES` in the same file. Read both before writing anything.
- Blueprints (question types, counts, word limits, level, style) for mocks: `MOCK_READING` in
  `backend/scripts/content/spec.py`. Practice blueprints are given in your task.
- Topics (`topic` slugs): `READING_TOPICS` in `spec.py`.

## File format

Pydantic models: `backend/scripts/content/schema.py` (`CSection`, `CPart`, `CPassage`, `CGroup`, `CQuestion`,
`Layout`). A complete practice file that passes every check: `content/tests/practice-reading-psychology-01.json`;
a mock section: the reading section of `content/tests/mock-01.json`.

A reading part:
```json
{"number": 1, "context": "academic_reading", "topic": "biology-ecology",
 "passage": {"title": "...", "paragraphs": [{"label": "A", "text": "..."}, ...], "glossary": []},
 "groups": [{"qtype": "tfng", "instructions": "", "max_words": null, "allow_number": false, "pick": 1,
             "options": null, "layout": null, "questions": [...]}]}
```
- `instructions` stays "": the pipeline writes the exact rubric (and the paragraph list for matching information).
- Each question: `number`, `prompt`, `options` (single-answer MCQ only), `answer` (list), `difficulty` 1–5,
  `sub_skill` (skimming | scanning | detail | inference | writer_view | paraphrase), `explanation`
  {`correct`, `distractors`: [{`option`, `why_wrong`}]}, `evidence` {`paragraph`: label, `quote`: an EXACT
  substring of that paragraph}.
- Passage length: 700–1,000 words (target 750–900), 5–8 paragraphs. A mock's three passages total 2,150–2,750
  words, 40 questions numbered 1–40 across the section, difficulty rising from passage 1 to 3.
- A practice test numbers its questions 1–N.

## Workflow (run from `backend/`)
```
export CONTENT_DIR=$PWD/../content JWT_SECRET=x DATABASE_URL=postgresql+asyncpg://x/x
uv run --quiet python -m scripts.content.offline check <slug>
```
- Practice: write `content/tests/<slug>.json` = `{"slug": ..., "kind": "practice", "title": <short title>,
  "status": "needs_review", "sections": [{"skill": "reading", "duration_s": null, "parts": [one part, number 1]}]}`.
- Mock section: write the `CSection` (`{"skill": "reading", "duration_s": 3600, "parts": [3 parts]}`) to
  `content/drafts/<mock>-reading.json`, and a work copy `content/tests/wip-<mock>-reading.json` = a test
  (`"kind": "mock"`, `"status": "needs_review"`) holding only that section, to run `check` on. The coordinator
  merges the draft into the mock; never edit `content/tests/<mock>.json` yourself.
- Repeat until `check` prints 0 check errors. Then run `view <slug>` once and read it as a candidate would:
  every question must have exactly one defensible answer.
- Do not run `finalize`: the coordinator does that after a blind solve.
