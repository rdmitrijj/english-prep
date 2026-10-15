# Brief: writing Listening content for English-prep

You write ORIGINAL listening recordings (as scripts) and questions for an exam simulator modelled on the
IELTS Listening test (computer-delivered). The scripts are turned into audio by a text-to-speech engine later.
Never reproduce or closely paraphrase published exam material. No real living people. British spelling in
narration; speakers may use their own accent's usual vocabulary.

## File format

Pydantic models: `backend/scripts/content/schema.py` (`CSection`, `CPart`, `CScript`, `Speaker`, `Line`, `CGroup`,
`CQuestion`, `Layout`). A complete small example that passes all checks: `backend/tests/listening_fixture.py`.

A listening part:
```json
{
  "number": 1, "context": "social_dialogue", "topic": "accommodation",
  "script": {
    "speakers": [{"id": "narrator", "role": "Narrator", "accent": "en-GB", "gender": "male"},
                 {"id": "agent", "role": "Letting agent", "accent": "en-AU", "gender": "female"}, ...],
    "lines": [{"speaker": "narrator", "text": "...", "pause_after_s": 30}, {"speaker": "agent", "text": "..."}, ...]
  },
  "audio": null,
  "groups": [ ... ]
}
```
- `context`: `social_dialogue` (Part 1: 2 speakers), `social_monologue` (Part 2: 1 main speaker, max 2),
  `academic_discussion` (Part 3: 2–4 speakers, e.g. students and a tutor), `academic_lecture` (Part 4: 1 speaker).
- `topic`: a slug. Everyday: accommodation, travel-transport, local-services, leisure-events, work-jobs,
  study-courses, health-fitness. Academic: biology-ecology, history-archaeology, psychology, linguistics-education,
  technology-engineering, earth-science-climate, health-medicine, business-economics, architecture-urban,
  agriculture-food, arts-culture, astronomy-physics.
- Accents: `en-GB`, `en-AU`, `en-NZ`, `en-US`, `en-CA`. Narrator is always `{"id": "narrator", "role": "Narrator",
  "accent": "en-GB", "gender": "male"}`. Each speaker id is lower-case, one word.
- Each line is one natural speaking turn (1–4 sentences). Put numbers the way they should be SAID and written,
  e.g. "It's 15 pounds" / "flat 3B" / "the 21st of May". Spell names letter by letter when a speaker would:
  "My surname's Hartley — H-A-R-T-L-E-Y." (the plain word must also appear, since answers are checked against it).

## Narration (exact pattern, from the real test)
- Start: "Part N. You will hear <situation>. First, you have some time to look at questions A to B." pause 30
- Then: "Now listen carefully and answer questions A to B." (no pause)
- If the part is split: "Before you hear the rest of the <conversation/talk>, you have some time to look at
  questions C to D." pause 30, then "Now listen and answer questions C to D."
- End: "That is the end of Part N. You now have half a minute to check your answers." pause 30
- Part 4 has NO break in the middle: one reading pause of 45 s for all ten questions.
- Practice recordings use the same pattern but without "Part N." at the start.

## Questions
Group shape is the same as Reading (`qtype`, `instructions` "" — the pipeline writes the exact rubric,
`max_words`, `allow_number`, `pick`, `options`, `layout`, `questions`). Each question: `number`, `prompt`,
`options` (single-answer MCQ only), `answer` (list), `difficulty` 1–5, `sub_skill`
(detail | paraphrase | inference | scanning…), `explanation` {`correct`, `distractors`: [{`option`, `why_wrong`}]},
`evidence` {`paragraph`: "" (filled automatically), `quote`: an EXACT substring of ONE line's text}.

Rules:
- Questions follow the order of the recording, without exception. Question numbers run 1–40 over a mock
  (10 per part), 1–N in a practice test.
- Gap answers are the exact words spoken, within the word limit; `answer` = [spoken form, acceptable variants
  such as "15" / "fifteen", UK/US spelling]. Words only when `allow_number` is false.
- Classic listening distractors: speakers mention wrong options first and then correct themselves, a date is
  changed, a second option is rejected. Every MCQ option is mentioned or alluded to; exactly one is right.
- `mcq` (single): own options A, B, C (three options). `mcq` with `pick: 2`: group options A–E, exactly 2
  questions with the same prompt, each `answer` = both letters, e.g. ["B", "D"].
- `matching`: group `options` = the box (letters A–G etc., at least questions + 1), `layout` = {"title":
  "<the question, e.g. What does the speaker say about each of the following places?>", "template": null,
  "table": null, "steps": null}; each question prompt = the item (e.g. "the museum"); answer = one letter.
- `form_completion` / `note_completion` / `table_completion` / `sentence_completion`: like Reading — layout
  template lines with gaps `{n}` (form: "Name: {1}" lines; notes: "- " bullets and short headings), sentence
  prompts contain "______". Prompt = a few words of context.
- Explanations name the paraphrase; distractor notes say why each wrong option is wrong (for MCQ every other
  letter; for gap-fills list tempting wrong words the speaker said, or leave the list empty).
- Difficulty rises: Part 1 easiest → Part 4 hardest.

## Length
At 2.6 words per second, a part is about 650–850 spoken words plus its pauses, i.e. 6.5–8 minutes. A mock's
four parts must total 26–32 minutes (the checker estimates this). Use at least 3 different accents across a mock
(not counting the narrator) and mix genders.

## Workflow (run from the repo root)
```
cd backend && CONTENT_DIR=../content JWT_SECRET=x DATABASE_URL=postgresql+asyncpg://x/x \
  uv run --quiet python -m scripts.content.offline <cmd> <slug> [...]
```
- Mock section: write a `CSection` JSON (`{"skill": "listening", "duration_s": null, "parts": [...4 parts]}`) to
  `content/drafts/<slug>-listening.json`, then `merge <slug> --file drafts/<slug>-listening.json`, then `check <slug>`.
  To fix errors, edit the draft and merge again.
- Practice test: write a full test to `content/tests/<slug>.json`:
  `{"slug": ..., "kind": "practice", "title": <short title>, "status": "needs_review", "sections": [{"skill":
  "listening", "duration_s": null, "parts": [one part, number 1]}]}`, then `check <slug>`.
- Repeat until `check` reports 0 check errors (errors starting with "L"). Do not edit any Reading section.
- Do not render audio and do not run finalize — the coordinator does that after a blind check.
