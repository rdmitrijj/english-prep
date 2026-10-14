# RESEARCH.md: IELTS Academic (computer-delivered), Phase 0

Researched on 2026-10-14. Every exam fact links to its source.
Labels used in this file:
- **[OFFICIAL]**: ielts.org, British Council (takeielts.britishcouncil.org), IDP (ielts.idp.com), Cambridge, or an official IELTS PDF.
- **[UNOFFICIAL]**: prep sites, blogs, aggregators. Use these for content mix only, never for scoring logic.
- **[INFERENCE]**: my own reasoning from official text. These are marked so you can challenge them.

Main sources (cited below by their short name):
- `ielts-L`: [ielts.org Academic Listening format](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-listening)
- `ielts-R`: [ielts.org Academic Reading format](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-reading)
- `ielts-W`: [ielts.org Academic Writing format](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-writing)
- `ielts-S`: [ielts.org Academic Speaking format](https://ielts.org/take-a-test/test-types/ielts-academic-test/ielts-academic-format-speaking)
- `ielts-scoring`: [ielts.org "IELTS scoring in detail"](https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail)
- `idp-cd`: [IDP "How computer-delivered IELTS works"](https://ielts.idp.com/prepare/article-how-computer-delivered-ielts-works)
- `idp-cd-ca`: [IDP Canada "IELTS on computer test format"](https://ielts.idp.com/canada/about/which-ielts-test/computer-delivered-ielts)
- `wbd`: [Writing Band Descriptors PDF, updated May 2023](https://ielts.org/cdn/ielts-downloadable-assets/ielts-guidance-and-support/ielts-guides/ielts-writing-band-descriptors.pdf)
- `kac`: [Writing Key Assessment Criteria PDF](https://ielts.org/cdn/Guides/ielts-writing-key-assessment-criteria.pdf)
- `sbd`: [Speaking Band Descriptors PDF](https://ielts.org/cdn/ielts-downloadable-assets/ielts-guidance-and-support/ielts-guides/ielts-speaking-band-descriptors.pdf)
- `samples`: [ielts.org computer-delivered sample questions (Academic)](https://www.ielts.org/take-a-test/preparation-resources/sample-test-questions/academic-test)

---

## 1. Delivery format in 2026

| Fact | Source |
|---|---|
| From mid-2026, paper-based IELTS is no longer offered and **all tests are delivered on computer**. Exact timelines vary by market. Announced on 05 Mar 2026. | [OFFICIAL] [ielts.org "Updates to IELTS test delivery"](https://ielts.org/news-and-insights/updates-to-ielts-test-delivery), [IDP news](https://ielts.idp.com/about/news-and-articles/article-updates-to-ielts-test-delivery) |
| Several prep sites name **27 June 2026** as the last paper date in most countries. The official text gives no specific date. | [UNOFFICIAL] [thelanguagefair.com](https://thelanguagefair.com/ielts-paper-exam-ending-2026-everything-you-need-to-know-before-june-27/), [testmimic](https://testmimic.com/guides/ielts/paper-based-ielts-discontinued) |
| **Writing on Paper** is a hybrid option in selected (unnamed) markets. Listening, Reading and Speaking are taken as normal; only the Writing answers are handwritten. One Skill Retake must use the same mode. | [OFFICIAL] ielts.org update (above); [BC IELTS on computer](https://takeielts.britishcouncil.org/what-is-ielts/how-it-works/test-modes/ielts-on-computer) |
| The change "does not change the IELTS skills assessed, the test construct, or the way results should be interpreted". | [OFFICIAL] ielts.org update |
| Speaking is still **face-to-face with a human examiner**. It is not done on the computer. | [OFFICIAL] `idp-cd`, `ielts-S` |
| UKVI SELT is digital-only. | [OFFICIAL] ielts.org update |

**What this means for the app:** we only need to simulate the computer-delivered (CD) format. Paper-specific rules, such as the 10-minute Listening transfer time and answer sheets, are not needed.

---

## 2. Academic exam specification

### 2.1 Listening ([OFFICIAL] `ielts-L`, `idp-cd`, `idp-cd-ca`)
- **4 parts × 10 questions = 40.** About 30 minutes; IDP gives **30–34 min** on computer (`idp-cd-ca`).
- **The recording is heard once only** (`ielts-L`).
- **No transfer time on computer.** There is a **2-minute review at the end** (`idp-cd`, `idp-cd-ca`). The paper test had 10 minutes of transfer time, which CD has dropped ([BC Tunisia](https://www.britishcouncil.tn/en/exam/ielts/computer-paper)).
- Before each part there is "some time to read the questions", and after each part there is "some time to review your answers". IDP gives **no exact duration** (`idp-cd-ca`).
  - [UNOFFICIAL / INFERENCE] In practice these pauses are built into the recording ("You now have some time to look at questions 1 to 5…"), at roughly 30 s per question block.
  - The Part 4 recording has **no break in the middle** ([OFFICIAL] [BC Listening format](https://takeielts.britishcouncil.org/what-is-ielts/how-it-works/test-format/listening)).
- **Questions follow the order of the information in the recording** (`ielts-L`).
- **Parts** (`ielts-L`):
  1. Everyday social context, **two speakers** (e.g. travel arrangements).
  2. Everyday social context, **one main speaker** (e.g. a speech about local facilities).
  3. Educational or training context, **two main speakers** (e.g. students, possibly guided by a tutor). IDP says "**up to four** people", and the official sample transcript has four speakers: M1, F1, F2, M2 ([sample transcript PDF](https://ielts.org/cdn/computer-delivered-sample-tests-listening/ielts-listening-computer-delivered-multiple-choice-one-answer-transcript.pdf)).
  4. Educational or training context, **monologue on an academic subject**.
- **Accents:** "British, Australian, New Zealand and North American" (`ielts-L`).
- **Difficulty progression:** Part 1 is easiest and Part 4 hardest. [UNOFFICIAL] Not stated as a rule on ielts.org, but consistent across prep sources ([ieltsliz](https://ieltsliz.com/ielts-listening-test-sections/)).
- **Marking:** 1 mark per correct answer. The raw score converts to a band in whole or half bands.

### 2.2 Academic Reading ([OFFICIAL] `ielts-R`)
- **60 minutes, 3 sections (one long text each), 40 questions.** No extra transfer time.
- **Total length 2,150–2,750 words**, so about 720–920 words per passage on average. [INFERENCE] The per-passage figure is just the total divided by 3.
- Texts come from books, journals, magazines, newspapers and online resources. They are written for non-specialists, on topics of general interest at undergraduate or postgraduate level.
- Styles are narrative, descriptive, or discursive/argumentative. **At least one text contains detailed logical argument.** Texts may include diagrams, graphs or illustrations. Technical terms get a simple glossary.
- Marking is 1 mark per question.

### 2.3 Academic Writing ([OFFICIAL] `ielts-W`, `kac`)
- **60 min total, 2 tasks, both must be completed.**
- **Task 1:** at least 150 words, about 20 min advised. The input is one or more graphs, charts or tables, or a diagram of an object, device, process or event. `kac` also lists **maps**. Use an academic or semi-formal/neutral style.
- **Task 2:** at least 250 words, about 40 min advised. The candidate responds to a point of view, argument or problem, supported with examples or evidence.
- **"Task 2 contributes twice as much as Task 1 to the Writing score."** Confirmed on `ielts-W`. `kac` says only "carries more weight". The exact rounding of the combined Writing score is **not published**. See the open questions.
- Write full connected text. **Notes or bullet points are penalised** (`kac`). Plagiarised text is severely penalised (`ielts-W`).
- Notes typed in the note tool are not seen by the examiner (`ielts-W`).

### 2.4 Speaking ([OFFICIAL] `ielts-S`)
- **11–14 min, 3 parts, face-to-face, recorded.**
- **Part 1 (4–5 min):** the examiner introduces themselves and checks identity, then asks about familiar topics (home, family, work, studies, interests).
- **Part 2 (3–4 min including prep):** the candidate gets a task card and has **1 minute to prepare** with pencil and paper, then talks for up to **2 minutes**. The examiner stops them at the time limit and may ask 1–2 follow-up questions.
- **Part 3 (4–5 min):** a more abstract discussion linked to the Part 2 topic.
- Criteria: Fluency and Coherence, Lexical Resource, Grammatical Range and Accuracy, Pronunciation. All are weighted equally (`ielts-scoring`).

---

## 3. Question types, instruction wording and marking rules

### 3.1 Listening question types ([OFFICIAL] `ielts-L`)
1. **Multiple choice:** a question with 3 options, or a sentence stem with 3 endings. Some items choose **more than one** answer from a longer list.
2. **Matching:** match items to a list of lettered options.
3. **Plan / map / diagram labelling:** answers are usually chosen from a list of letters.
4. **Form / note / table / flow-chart completion:** either choose from a list or write words from the recording within the word limit.
5. **Sentence completion.**
6. **Short-answer questions:** some ask for 2–3 answers.

### 3.2 Academic Reading question types ([OFFICIAL] `ielts-R`)
1. **Multiple choice:** **4 options** (Listening has 3), single or multiple answers.
2. **True / False / Not Given** (identifying information). "False" means the statement contradicts the text. "Not given" means the text neither agrees with nor contradicts it.
3. **Yes / No / Not Given** (the writer's views or claims).
4. **Matching information:** details to paragraphs. A paragraph may be unused or used more than once.
5. **Matching headings:** there are **more headings than paragraphs**, and each heading is used at most once.
6. **Matching features:** statements to a list of options, such as people or dates. Options may be reused.
7. **Matching sentence endings:** there are more endings than beginnings.
8. **Sentence completion:** words from the text, within a word limit.
9. **Summary / note / table / flow-chart completion:** words from the text **or** chosen from a list.
10. **Diagram label completion.**
11. **Short-answer questions:** answers follow the order of the text.

### 3.3 Instruction wording
- **Paper-style wording, as an example from the official page:** "NO MORE THAN TWO WORDS AND/OR A NUMBER" (`ielts-L`, `ielts-R`).
  - [UNOFFICIAL, but the long-standing standard wording in Cambridge-published tests] Other limit variants: "ONE WORD ONLY", "ONE WORD AND/OR A NUMBER", "NO MORE THAN TWO WORDS", "NO MORE THAN THREE WORDS AND/OR A NUMBER". Other standard rubrics: "Choose the correct letter, A, B or C" and "Choose TWO letters, A–E". For TFNG: "Do the following statements agree with the information given in Reading Passage 1? Write TRUE if…, FALSE if…, NOT GIVEN if…".
- **Computer-delivered wording** from the official CD samples (`samples`):
  - Gap fills: "For each question, write your answer in the gap."
  - Multiple choice: "For each question, click on the correct answer." / "Click on the correct answers."
  - Table items: "For each question, click on the correct space in the table."
  - **Drag-and-drop:** "For each question, click on the correct answer and **move it into the gap**."
  - Listening intro: "You will hear each recording ONCE only."
- **What this means for the app:** in CD format, matching and labelling-from-a-list are done by **drag-and-drop** or by clicking a table cell, not by typing letters. Word limits are still written in the rubric.

### 3.4 Marking of written answers (Listening and Reading)
| Rule | Source |
|---|---|
| Going over the word limit **loses the mark**. | [OFFICIAL] `ielts-L`, `ielts-R` |
| **Hyphenated words count as one word** ("check-in"). Contractions are not tested. | [OFFICIAL] `ielts-L`, `ielts-R` |
| Listening: words do not need to be changed from the recording. Reading short answers: numbers may be written as figures or as words. | [OFFICIAL] `ielts-L`, `ielts-R` |
| A number written in words counts as one number ("three hundred and twenty" = 320). | [OFFICIAL-adjacent] [IDP listening tips](https://ielts.idp.com/thailand/prepare/article-question-types-listening) |
| **Misspelt answers are marked wrong.** | [OFFICIAL] [IDP "How to spell"](https://ielts.idp.com/prepare/article-ielts-how-to-spell), [IELTS Information for Candidates PDF](https://takeielts.britishcouncil.org/sites/default/files/[downloads]/ielts_information_for_candidates_us_version.pdf) |
| **British and American spellings are both accepted.** | [OFFICIAL] [BC blog](https://takeielts.britishcouncil.org/blog/british-or-american-english-ielts), IDP (above) |
| Upper or lower case are both accepted; answers may be written entirely in capitals. | [OFFICIAL] Information for Candidates PDF |
| [UNOFFICIAL] Wrong singular/plural is usually marked wrong. Official answer keys list accepted variants with `/` and optional words in `( )`. | Seen in published answer keys; not a stated official rule |

**What this means for answer normalisation:** make answers case-insensitive, collapse whitespace, and treat hyphenated words as one word when counting. Accept both UK and US spellings and figure/word variants, but only through each item's explicit **accepted-variants list**. Never use fuzzy matching, because real misspellings must stay wrong.

---

## 4. Raw score → band conversion

ielts.org publishes **only anchor points** and says the precise number of marks "varies slightly from test version to test version" (`ielts-scoring`).

| Band | Listening (raw /40) | Academic Reading (raw /40) |
|---|---|---|
| 5 | 16 | 15 |
| 6 | 23 | 23 |
| 7 | 30 | 30 |
| 8 | 35 | 35 |

**Full table (Listening)**, [OFFICIAL] IDP (an IELTS co-owner), described as "the average number of marks required" ([IDP Listening scores](https://ielts.idp.com/vietnam/results/scores/listening/en-gb)):

| Raw | 39–40 | 37–38 | 35–36 | 32–34 | 30–31 | 26–29 | 23–25 | 18–22 | 16–17 | 13–15 | 11–12 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Band | 9 | 8.5 | 8 | 7.5 | 7 | 6.5 | 6 | 5.5 | 5 | 4.5 | 4 |

**Full table (Academic Reading)**, [UNOFFICIAL]. This is the widely reproduced table (as printed in Cambridge IELTS books). It is consistent with all four official anchors, but I could not find it on an official web page ([cathoven](https://resources.cathoven.com/ielts-reading/band-scores), [ece.edu.vn](https://ece.edu.vn/en/how-to-calculate-your-ielts-band-score-for-all-4-skills-and-overall/)):

| Raw | 39–40 | 37–38 | 35–36 | 33–34 | 30–32 | 27–29 | 23–26 | 19–22 | 15–18 | 13–14 | 10–12 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Band | 9 | 8.5 | 8 | 7.5 | 7 | 6.5 | 6 | 5.5 | 5 | 4.5 | 4 |

Neither table goes below band 4. **What this means for the app:** store these as versioned `band_tables` rows. For scores below the table, we need our own extrapolation, clearly labelled.

---

## 5. Overall band rounding ([OFFICIAL] `ielts-scoring`, [IDP calculator](https://ielts.idp.com/canada/results/how-ielts-is-marked/ielts-score-calculator))
- Overall = average of the four section bands, rounded to the nearest half band. **An average ending in .25 rounds up to the next half band, and one ending in .75 rounds up to the next whole band.**
- Official examples: 6.25 → 6.5; 3.875 → 4.0; 6.125 → 6.0.
- **The rule, verified:** `overall = floor(avg * 2 + 0.5) / 2`, i.e. round half up on a 0.5 grid. It reproduces all three examples.

---

## 6. Writing and Speaking band descriptors

### 6.1 Writing (May 2023 revision, `wbd`)
- **Four criteria per task, weighted equally.** The task score is their average (`ielts-scoring`):
  - TA (Task 1) or TR (Task 2)
  - CC (Coherence and Cohesion)
  - LR (Lexical Resource)
  - GRA (Grammatical Range and Accuracy)
- The 2019–2023 revision was for clarity; the criteria did not change ([research summary](https://ielts.org/researchers/our-research/research-reports/ielts-writing-scales-review-and-update-summary-overview)).
- Rating rule printed on every page: **"A script must fully fit the positive features of the descriptor at a particular level. Bolded text indicates negative features that will limit a rating."** This supports your brief's "award the lower band" rule.

**Summary of band 5 → 9 distinctions** (condensed from `wbd`):

| Band | TA (T1 Academic) | TR (T2) | CC | LR | GRA |
|---|---|---|---|---|---|
| 9 | All requirements fully and appropriately satisfied | Prompt explored in depth; fully developed position | Effortless to follow; cohesion rarely attracts attention | Full flexibility and precision; sophisticated control; very rare minor slips | Wide range, full flexibility and control; errors extremely rare |
| 8 | Key features skilfully selected, highlighted and illustrated | Sufficiently addressed; well-developed position; ideas well extended and supported | Logically sequenced; cohesion well managed; occasional lapses | Skilful use of uncommon or idiomatic items; occasional collocation slips | Most sentences error-free; occasional non-systematic errors |
| 7 | **Clear overview; data appropriately categorised**; main trends or differences identified | Main parts addressed; clear position; may over-generalise | Clear progression; range of devices with some over- or under-use | Some less common items; awareness of style and collocation | Variety of complex structures; error-free sentences frequent |
| 6 | **Relevant overview attempted**; supported with data; some irrelevant or inaccurate detail | Main parts addressed (unevenly); position present but conclusions may be unclear; some ideas underdeveloped | Generally coherent; cohesion sometimes faulty or mechanical; paragraphing not always logical | Adequate; risk-taking brings inaccuracy | Mix of simple and complex; errors rarely impede communication |
| 5 | Key features not adequately covered; **mechanical recounting; may have no data to support the description**; focus on details without the bigger picture | **Main parts incompletely addressed**; position unclear in development; limited ideas | Organisation not wholly logical; limited or overused devices; **paragraphing may be inadequate or missing** | Limited but minimally adequate; frequent word-choice lapses; noticeable spelling errors | Limited, repetitive range; complex sentences faulty; frequent errors |

**Published hard rules and caps:**
| Rule | Status |
|---|---|
| **20 words or fewer → band 1** on all four criteria. | [OFFICIAL] `wbd` |
| **Totally memorised answer → band 0** (when there is proof). | [OFFICIAL] `wbd` |
| Copied rubric is discounted, i.e. not counted towards length or language. | [OFFICIAL] `wbd` band 1 |
| Off-topic → penalised; "entire response may be off-topic" sits at band 2 CC. | [OFFICIAL] `wbd`, `ielts-W` |
| Bullet points or notes → penalised. Plagiarism → penalised. | [OFFICIAL] `kac` |
| Memorised or formulaic "lexical chunks" are a **band 4 LR** feature. Over-dependence on memorised language is a **band 3** feature. | [OFFICIAL] `wbd` |
| **No Task 1 overview → TA capped at 5.** Band 7 requires a clear overview and band 6 requires "a relevant overview attempted"; the "must fully fit" rule then rules out band 6. | [INFERENCE] from `wbd` (widely taught) |
| **Under-length:** the May 2023 public descriptors contain **no fixed word-count penalty**. ielts.org only says a too-short answer "may not be enough evidence… to award higher bands". LR band 3 mentions "significantly underlength". | [OFFICIAL] `ielts-W`, `wbd`. A fixed cap such as "under 150 words → TA max 5" is **[UNOFFICIAL] folklore** |

### 6.2 Speaking (`sbd`)
| Band | Fluency & Coherence | Lexical Resource | Grammar | Pronunciation |
|---|---|---|---|---|
| 9 | Hesitation only for content | Total flexibility; idiomatic | Precise and accurate at all times | Full range of features; accent has no effect on intelligibility |
| 8 | Rare repetition; hesitation mostly content-related | Skilful less common and idiomatic items; effective paraphrase | Wide range; majority error-free | Wide range; sustained rhythm; easily understood |
| 7 | Long turns without noticeable effort; some mid-sentence hesitation | Some less common and idiomatic items; style and collocation awareness | Range used flexibly; error-free sentences frequent | All of band 6 plus some, not all, of band 8 |
| 6 | Willing to produce long turns; coherence lost at times; connectives not always appropriate | Enough to discuss at length; generally paraphrases | Mix of short and complex; frequent errors in complex structures that rarely impede | Range of features, variable control; occasional lack of clarity |
| 5 | Keeps going via repetition or self-correction or slow speech; overuses markers | Limited flexibility; paraphrase not always successful | Basic forms fairly well controlled; complex forms limited and nearly always erroneous | All of band 4 plus some of band 6 |

- Notes on `sbd`: "A candidate must fully fit the positive features"; "rated on their **average performance across all parts**".
- **What this means for pronunciation:** IELTS judges **intelligibility and the use of phonological features, not closeness to a native accent** ("Accent has minimal effect on intelligibility" at band 8). This matters when choosing a pronunciation-scoring tool (§10).

---

## 7. The computer-delivered interface

| Element | Detail | Source |
|---|---|---|
| Timer | "Stopwatch in the **upper middle** part of the screen." It **flashes in the last 10 and 5 minutes** of Reading and Writing. Flashing is not documented for Listening. | [OFFICIAL] `idp-cd` |
| Timer turns red | Turns red at 10 and 5 minutes. | [UNOFFICIAL] [allearsenglish](https://www.allearsenglish.com/computer-delivered-reading-exam/) |
| Hide / break | A **"Hide"** button (upper right) hides the screen for a break; "Resume test" brings it back. | [OFFICIAL] `idp-cd` |
| Settings | **Settings** (upper right): font size and background colour. | [OFFICIAL] `idp-cd` |
| Help | A **Help** button shows instructions. | [OFFICIAL] `idp-cd`, [BC](https://takeielts.britishcouncil.org/what-is-ielts/how-it-works/test-modes/ielts-on-computer) |
| Tutorial | Each section starts with a video tutorial. | [OFFICIAL] [BC blog](https://takeielts.britishcouncil.org/blog/ielts-on-computer-changes-updates) |
| Navigation | A **navigation bar at the bottom** shows all question numbers, with forward/back arrows. Questions can be answered in any order and changed or left blank. | [OFFICIAL] `idp-cd` |
| Review flag | A **"Review"** button (lower left) marks the current question, and its number changes **from a square to a circle**. | [OFFICIAL] `idp-cd` |
| Reading layout | **Passage on the left, questions on the right**. The question pane scrolls. | [OFFICIAL] `idp-cd`, [IDP Reading tips](https://ielts.idp.com/mauritius/about/news-and-articles/article-tips-for-ielts-reading-test-on-computer) |
| Highlight and notes | Select text and **right-click → highlight**, or add a note. Notes open in a **separate split window on the right that can be shown or hidden**. Highlighting works on the passage (and reportedly the questions). There is no highlighting in Listening. | [OFFICIAL] `idp-cd`, BC blog; [UNOFFICIAL] [widerai](https://www.widerai.us/blog/ielts-reading-computer-based) |
| Writing layout | **Task on the left, answer box on the right.** Either task can be done first. **Live word count, lower left.** | [OFFICIAL] `idp-cd`, [IDP guide](https://ielts.idp.com/prepare/article-ielts-on-computer-guide-to-unlock-study-goals) |
| Copy and paste | **Cut, copy and paste are available** in Writing, from your own text and notes. | [OFFICIAL] [BC booking page](https://takeielts.britishcouncil.org/book-ielts-test/computer) |
| Spellcheck | **No official statement.** One prep site wrongly claims spellcheck exists. A language test cannot offer it. | [INFERENCE]; contradiction noted from [UNOFFICIAL] [ece.edu.vn](https://ece.edu.vn/en/ielts-on-computer-your-ultimate-guide-to-success-at-idp/) |
| Volume | Volume control bar, upper right. | [OFFICIAL] `idp-cd` |
| Listening answers | Typed while listening. A 2-minute review at the end. | [OFFICIAL] `idp-cd` |
| Time-out | "Your answers are saved and the system automatically shuts down." | [OFFICIAL] `idp-cd` |
| Test engine | The official CD samples run in the **Inspera** player (ielts.inspera.com). The real test is reportedly the same system. | [OFFICIAL] `samples` |

**What this means for the brief:** "disable spellcheck" is correct. Copy/paste should stay **enabled**, because the real test has it. We will reproduce the Hide, Settings and Help buttons.

---

## 8. Most frequent topics: ALL [UNOFFICIAL]

The test owners publish **no topic syllabus**. Every list below is compiled by prep sites from past papers and candidate reports.

**Writing Task 2 themes.**
- IDP's list ([IDP Vietnam](https://ielts.idp.com/vietnam/prepare/article-ielts-topic-writing-task-2/en-gb)): health, environment, education, technology, travel & tourism, family, sport, globalisation, government & society, crime & punishment.
- One estimated frequency breakdown ([cathoven](https://resources.cathoven.com/ielts-writing-task-2/topics-2026)): education ~22%, technology ~20%, environment ~18%, health ~15%, government/economy ~15%.
- Also recurring: work, urbanisation, media/advertising, culture, transport.
- **Essay types** (IDP): opinion (agree/disagree), discussion (both views), advantages/disadvantages, problem/solution (or cause/solution), two-part question.

**Task 1 visual types.**
- The seven commonly listed types ([IDP](https://ielts.idp.com/nigeria/prepare/article-ielts-writing-task-1-question-types), [ted-ielts](https://ted-ielts.com/ielts-academic-writing-task-1-types/)): line graph, bar chart, pie chart(s), table, mixed/multiple charts, process diagram, map (before/after).
- **There is no reliable frequency data.** Prep sites agree that line graphs and bar charts are most common, with maps and processes less frequent.
- Proposed content weighting, to be confirmed in PLAN: line 20%, bar 20%, table 15%, pie 10%, mixed 15%, process 10%, map 10%.

**Reading subject areas** ([oneielts](https://oneielts.com/ielts/reading/topics)):
- Biology, ecology and zoology
- History and archaeology
- Psychology, education and linguistics
- Technology and engineering
- Earth science, climate and geology
- Health and medicine
- Business and economics
- Architecture and urban planning
- Agriculture, food and nutrition
- Arts and culture

**Listening scenarios** ([IDP common listening topics](https://ielts.idp.com/vietnam/about/news-and-articles/article-common-ielts-listening-topics/en-gb), [ieltsliz](https://ieltsliz.com/ielts-listening-test-sections/)):
- **P1:** bookings and enquiries (accommodation, courses, restaurants, events), lost property, registrations. Answers are names, numbers, dates and addresses, so spelling-out is common.
- **P2:** tour guides, facility or site introductions, volunteer briefings, radio announcements. **Map labelling is most common here.**
- **P3:** students and a tutor discussing assignments, research projects or presentations, often with disagreement between speakers.
- **P4:** lectures on science, history, environment, psychology or business.

**Speaking topic banks** ([IDP Nepal](https://ielts.idp.com/nepal/about/news-and-articles/article-common-ielts-speaking-topics), [IDP Thailand cue cards](https://ielts.idp.com/thailand/about/news-and-articles/article-cue-card-topics-for-speaking-test), [IDP Part 3](https://ielts.idp.com/nepal/prepare/speaking/part-3-topics-and-questions)):
- **P1:** work or studies (usually the first question), home/accommodation, hometown, family, hobbies, food, weather, music, reading, transport, phones/technology, sport, shopping, friends, sleep, holidays.
- **P2** cue-card families: "Describe a person / place / object / event / experience / activity / piece of media". Examples include a place you visited, an influential person, a memorable journey, a time you solved a problem.
- **P3:** abstract follow-ups such as society, education, technology, environment, culture, media, work.

**Topic rotation.** Speaking topics are claimed to rotate "every 4 months" (Jan/May/Sep), with about half of the previous topics retired each time. **This is unverifiable.** The only sources are prep blogs, and some of them are low quality ([ielts-assistant](https://ielts-assistant.com/blog)). Treat it as folklore.

---

## 9. TTS for Listening audio

**Requirements:** distinct voices per speaker; **British, Australian, NZ and North American** accents (the official mix); natural dialogue; pre-generated audio; personal use.

Size of one full Listening test: 4 parts × about 700–900 words of script, plus rubric narration ≈ **22,000 characters** (≈ 25 min of audio). [INFERENCE] estimate.

| Option | Accent coverage | Quality / notes | Approx. cost per full test | Licensing for personal use |
|---|---|---|---|---|
| **Azure Neural TTS** | **Real locale voices**: `en-GB`, `en-AU`, `en-NZ`, `en-US`, `en-CA`, `en-IE`, each with several male and female voices. HD voices exist for these locales ([MS language support](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support)). | Very good. SSML gives exact `<break>` pauses, prosody and number reading. Slightly less "acted" than ElevenLabs. | ~$16 per 1M chars → **~$0.35** ([UNOFFICIAL] [texttolab](https://texttolab.com/blog/azure-text-to-speech-pricing)). **F0 free tier: 0.5M chars/month** ([OFFICIAL] [Azure pricing](https://azure.microsoft.com/en-us/pricing/details/speech/)), which covers ~20 tests/month for $0. | Standard Azure terms; output usable in your own app. |
| **ElevenLabs** | Large voice library with UK, AU and US voices (community voices vary in quality). | Most expressive and natural; v3 has dialogue mode. | ~$0.08 per 1k chars → **~$1.80** on the API. Plans from $6/mo ([UNOFFICIAL] [cartesia](https://www.cartesia.ai/learn/elevenlabs-pricing)). Prices moved in Sep–Oct 2026, so verify. | **The free tier carries no commercial licence and requires attribution.** Starter and above are fine. |
| **OpenAI `gpt-4o-mini-tts`** (snapshot `-2025-12-15`) | **No accent-specific voices.** Accent is requested through `instructions` ("speak with an Australian accent"). This is not guaranteed and quality varies by accent. | Good and steerable, but the voices are US-centric. | $0.60/1M input + $12/1M audio output → **~$0.40** ([OFFICIAL] [model page](https://developers.openai.com/api/docs/models/gpt-4o-mini-tts)) | OpenAI policy requires disclosing to users that the voice is AI-generated. That is trivial for personal use. |
| **Google Chirp 3 HD / Gemini-TTS** | en-GB, en-AU and en-US voices. Gemini-TTS supports **multi-speaker** with style prompts. | Very good. | Chirp 3 HD $30/1M → **~$0.66** ([OFFICIAL] [GCP pricing](https://cloud.google.com/text-to-speech/pricing)) | Standard GCP terms. |

> **Decision (2026-10-14): ElevenLabs** (user's choice), behind a swappable provider seam. See PLAN §6.6. Current model is `eleven_v4` at $0.08 per 1k chars ([ElevenLabs models](https://elevenlabs.io/docs/overview/models), [API pricing](https://elevenlabs.io/pricing/api)).

**Original recommendation: Azure Neural TTS.**
- It is the only option with **genuine voices in all four accent families the exam names**, including New Zealand.
- SSML gives deterministic pauses, which we need to build the "now look at questions 1–5" reading time into the audio.
- The free tier covers the whole MVP content build.
- The same Azure Speech resource also offers **Pronunciation Assessment**, relevant to §10.

The cost is a second vendor account next to OpenAI. If you'd rather keep one vendor, OpenAI TTS works but the accents become "best effort". Before committing, I suggest an A/B listen: one Part 1 script rendered on Azure and on ElevenLabs.

---

## 10. OpenAI Realtime API (for the optional Speaking examiner)

| Fact | Source |
|---|---|
| `gpt-realtime-2` exists, as your brief said. It has since been superseded: **`gpt-realtime-2.1` and `gpt-realtime-2.1-mini` were released on 6 Jul 2026**, with better silence and interruption handling and configurable reasoning effort. | [OFFICIAL] [gpt-realtime-2](https://developers.openai.com/api/docs/models/gpt-realtime-2), [gpt-realtime-2.1](https://developers.openai.com/api/docs/models/gpt-realtime-2.1); [UNOFFICIAL] [datanorth](https://datanorth.ai/news/openai-releases-gpt-realtime-2-1-voice-models) |
| `gpt-realtime-2.1` pricing per 1M tokens: **audio** $32 in / $0.40 cached / $64 out; **text** $4 in / $0.40 cached / $24 out. 128k context. Function calling supported. | [OFFICIAL] model page |
| Metering: **user audio = 1 token per 100 ms** (600/min), **assistant audio = 1 token per 50 ms** (1,200/min). **The whole conversation is re-sent as input on every response**, so cost grows over a session. Caching helps, but it is best-effort. | [OFFICIAL] [Realtime costs guide](https://developers.openai.com/api/docs/guides/realtime-costs) |
| **Estimate for one 14-min Speaking test** [INFERENCE]: candidate ~9 min (5.4k tokens), examiner ~3.5 min (4.2k output tokens, ≈ $0.27), and ~40 turns of growing context, mostly cached. **≈ $0.50–1.50 per test.** If caching fails it can reach several dollars, so we need a hard cap and per-session usage logging. | Derived from the two rows above |
| **WebRTC is recommended for browsers.** WebSocket suits server-to-server. | [OFFICIAL] [Realtime WebRTC guide](https://developers.openai.com/api/docs/guides/realtime-webrtc) |
| **Ephemeral key flow:** the backend calls `POST /v1/realtime/client_secrets` with the real API key and a `session` body (`type: "realtime"`, `model`, voice, etc.). The response `value` is an `ek_…` key. The browser posts its SDP offer to `POST /v1/realtime/calls` using that key. An `OpenAI-Safety-Identifier` header can be bound at mint time. Alternative "unified interface": the backend proxies the SDP to `/v1/realtime/calls` itself, which is simpler but puts our server in the setup path. | [OFFICIAL] same guide |
| **New alternative: GPT-Live-1** (API since 10 Sep 2026). A full-duplex voice model at **$0.05/min** (≈ $0.70 per test), using `POST /v1/live/sessions`. **No structured outputs.** Community reports say it does not support control events like `session.update` or `response.cancel`, which makes it **harder to script a strict exam**. | [OFFICIAL] [GPT-Live-1 model](https://developers.openai.com/api/docs/models/gpt-live-1), [Live guide](https://developers.openai.com/api/docs/guides/live); [UNOFFICIAL] [community](https://community.openai.com/t/introducing-gpt-live-1-in-the-api/1396471) |
| **Can it judge pronunciation from audio?** The model hears audio, but there is **no evidence that its numeric pronunciation scores are reliable**. A 2025 study found GPT-4o realtime less accurate than baseline models at predicting pronunciation scores, with frequent malformed JSON. | [arXiv 2503.11229](https://arxiv.org/abs/2503.11229) |
| Alternative: Azure **Pronunciation Assessment** has an unscripted mode with accuracy, fluency and prosody scores. **Caveat:** it measures closeness to a native model, not IELTS "intelligibility", and prosody/content may be en-US only (as of 2024; verify). | [OFFICIAL] [Azure docs](https://docs.azure.cn/en-us/ai-services/speech-service/pronunciation-assessment-tool); [MS Q&A](https://learn.microsoft.com/en-sg/answers/questions/1822620/azure-prononciation-assessment) |

**Recommendation:** use `gpt-realtime-2.1` for the live examiner (tools let the app control part transitions). Run post-test scoring on the text transcript with a text model. Label pronunciation clearly as an **estimate**, or mark it "not assessed".

---

## 11. Copyright and trade mark boundary

| Fact | Source |
|---|---|
| ielts.org material is for **personal, non-commercial use only**. **No republishing on another website and no modification** without written permission. | [OFFICIAL] [IELTS copyright & trade mark statement](https://ielts.org/legal/ielts-copyright-and-trade-mark-statement) |
| **"IELTS" and the IELTS logos are registered trade marks.** "You must not use, copy, reproduce, modify, distribute, republish, display or communicate these trade marks in any way" without permission. | [OFFICIAL] same page |
| The IDP site's content is copyright-protected and may not be reproduced. | [OFFICIAL] [IDP terms](https://ielts.idp.com/prepare/article-terms-and-conditions) |
| Cambridge IELTS books are copyrighted by Cambridge University Press & Assessment. | General knowledge, consistent with the above |

**Policy for the app:**
- All passages, scripts, prompts, charts and audio are **original**.
- The official band descriptors are used as **evaluator guidance** (paraphrased and summarised in our prompts), not republished in the UI.
- Official practice tests are **linked only**: the [ielts.org samples](https://www.ielts.org/take-a-test/preparation-resources/sample-test-questions/academic-test) and the [BC familiarisation test](https://takeielts.britishcouncil.org/take-ielts/prepare/free-ielts-english-practice-tests/ielts-on-computer/familiarisation-test).
- **The app name and branding should not use the "IELTS" mark or logo**, because the site will be public. A descriptive line such as "practice for the IELTS Academic test" is lower risk, but I am not a lawyer.

---

## Open questions and contradictions found

1. **Writing score rounding.** `(T1 + 2·T2) / 3` is confirmed, but the rounding of that result is not published. Proposed: round to the nearest 0.5 using the same half-up rule as §5. Needs your OK.
2. **Academic Reading full table** is unofficial (official anchors only).
3. **Listening reading-time durations** are not stated officially. We will use ~30 s per block (Part 4 ~45–60 s) as an assumption.
4. **Brief vs research:**
   - The brief says "disable spellcheck/autocorrect". Agreed.
   - Copy/paste should stay ON, because the real test has it.
   - The brief's "Task 1 under 150 words" hard cap is not in the current public descriptors.
5. **Environment:** the brief says Windows 11 + PowerShell, but this session runs on **Arch Linux**. Which is your real dev machine?
