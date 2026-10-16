# Writing content brief (M6)

You author original IELTS-Academic-style Writing tasks for the English-prep app as JSON files.
Never copy or closely paraphrase Cambridge, IDP, British Council or ielts.org tasks: every prompt, number and
diagram is original (RESEARCH §11). Never put "IELTS" in titles.

## File format

A practice task is one test file, `content/tests/<slug>.json`:

```json
{
  "slug": "practice-writing-t1-bar-01",
  "kind": "practice",
  "title": "Bar chart: weekly exercise by age group",
  "status": "needs_review",
  "sections": [{"skill": "writing", "duration_s": null, "parts": [PART]}]
}
```

A mock task is one PART in `content/drafts/<name>.json` (the lead merges them into mock-01).

PART for **Task 1** (`number` = 1):

```json
{
  "number": 1, "context": "writing_task1", "topic": "health",
  "writing": {
    "task_number": 1,
    "prompt": "The bar chart below shows the average number of hours per week that men and women in one country spent exercising, by age group, in 2023.",
    "visual": {"type": "bar", "charts": [CHART], "description": null, "url": null}
  }
}
```

CHART (drawn automatically from these numbers; never draw charts by hand):

```json
{"type": "bar", "title": "Average weekly hours of exercise, by age group (2023)", "unit": "hours per week",
 "categories": ["16–24", "25–34", "35–44", "45–54", "55+"],
 "series": [{"name": "Men", "values": [5.2, 4.1, 3.3, 2.9, 2.2]}, {"name": "Women", "values": [4.0, 3.6, 3.1, 2.8, 2.4]}]}
```

- `line`: categories = the x-axis points (usually years); one series per line (2–4 lines).
- `bar`: categories = bar groups; one series per bar colour (1–3).
- `pie`: categories = slices (4–6); one series per pie (1–2 pies, e.g. two years); each pie adds up to 100.
- `table`: categories = row labels (4–6); series = columns (3–4).
- `mixed`: `"type": "mixed"` with exactly two CHARTs of different types (e.g. a bar + a pie, or a line + a table).
- `process` / `map`: `charts: []`, a hand-drawn SVG file, and a `description` (see below).

PART for **Task 2** (`number` = 2):

```json
{
  "number": 2, "context": "writing_task2", "topic": "education",
  "writing": {"task_number": 2, "essay_type": "opinion",
              "prompt": "Some people believe that university education should be free for every student.\n\nTo what extent do you agree or disagree?"}
}
```

`prompt` holds ONLY the task's own words. The fixed lines ("You should spend about 20 minutes…",
"Summarise the information…", "Write about the following topic:", "Give reasons for your answer…",
"Write at least … words") are added by the app. Never write them, and never write "at least".

Topics (`topic`): education, technology, environment, health, work-economy, government-law, society-family,
media-culture, cities-transport, travel-tourism, energy-resources.

Essay types (`essay_type`) and their real question forms:
- `opinion`: "… To what extent do you agree or disagree?"
- `discussion`: "Some people think … Others believe … Discuss both these views and give your own opinion."
- `advantages_disadvantages`: "… Do the advantages of this outweigh the disadvantages?"
- `problem_solution`: "… What problems does this cause? What solutions can you suggest?" (or causes/measures)
- `two_part`: two direct questions, e.g. "Why is this happening? Is it a positive or negative development?"

## Quality bar

- Task 1: one sentence in the real style: "The line graph below shows … in … between … and …". The data must have
  a clear overview story (a main trend, a crossover, a biggest/smallest), plus 2–3 notable details. Realistic but
  invented numbers, a specific place/time, units stated. Not so much data that 150–200 words can't cover it.
- Task 2: a debatable statement on a common theme, neutral, answerable by any adult without specialist knowledge,
  1–3 sentences + the question form. Vary the wording; avoid the most famous textbook prompts.

## Process diagrams and maps

Draw an SVG by hand at `content/media/visuals/<slug>-t1.svg` and set `"url": "/media/visuals/<slug>-t1.svg"`.
- `viewBox="0 0 900 560"`, white background rect, `font-family="DejaVu Sans, Arial, sans-serif"`, font-size ≥ 14,
  black or dark-grey strokes, at most 3 muted fill colours. Plain and schematic like an exam diagram.
- Title text at the top. Process: 6–9 numbered stages with short labels and arrows (one may branch or loop).
  Maps: two maps side by side with years as headings (e.g. "1995" and "Today"), a north arrow, a scale bar or
  key, and 6–10 labelled features of which several change.
- No overlapping text; every label inside the canvas. Check it: `rsvg-convert -w 900 file.svg -o /tmp/x.png`
  then view the PNG, and fix anything cramped or overlapping.
- `description`: a precise paragraph listing every stage in order (process) or every feature in both maps and each
  change (map). The examiner reads ONLY this text, so anything in the picture must be in it, and nothing else.

## Commands (from `backend/`)

```bash
export PYTHONPATH=. DATABASE_URL=postgresql+asyncpg://x@localhost/x JWT_SECRET=x CONTENT_DIR=$PWD/../content
uv run python -m scripts.content.visuals render <slug>   # Task 1 charts: draws the SVG, then runs every check
uv run python -m scripts.content.offline check <slug>    # Task 2, process and map: runs every check
```

A file is done when it prints `published` with 0 check errors. Look at every rendered chart
(`rsvg-convert` → PNG → view it): if labels overlap or the story is unclear, change the data or labels and render again.
