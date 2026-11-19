# ProbCheck: an evidence-checking study assistant for probability

Intelligent Interactive Systems · A2 project · student 3098204
README prose: about 1,840 words (code blocks and commands not counted).

ProbCheck helps a first-year student decide whether to trust an explanation of a probability
question. Each sentence of the answer links to the course-note passage it relies on. Numbers are
recalculated in code. A verbal cue says how far the answer was checked. When the question is
ambiguous, the system asks instead of guessing.

**Submitted version:** tag `v1.3-a2` (commit hash on the report's first page). Earlier tags: `v1.0-a2` (9 November baseline), `v1.1-a2` (17 November), `v1.2-a2` (19 November).

## Project status

| Part | Status |
|---|---|
| Question parsing with a visible, editable interpretation (`parse.py`) | Implemented (rule-based) |
| Gate: clarify unclear events, reject impossible or inconsistent values (typed question and correction form; P(A∩B) = 0 is applied when events are mutually exclusive), decline out-of-scope questions | Implemented |
| Deterministic checks: independence, mutually exclusive + independent, addition rule, conditional probability (`checker.py`) | Implemented |
| Retrieval with source, section, date, score; superseded passages ranked last and labelled (`retrieve.py`) | Implemented |
| Per-sentence screening of the model's wording: citation, current source, allowed numbers, word overlap (`verify.py`) | Implemented; does not check that the meaning is correct |
| Page: uncertainty cue ("Screened against the notes" states what the screening covers), one-click source highlight, correction form with a mutually-exclusive checkbox, mismatch report, removed-sentence list | Implemented |
| Revision-slot tool with validation, confirmation and log (`tools.py`) | Implemented (carried over from Lab 4, now with a topic) |
| Language model that words the checked facts | **Simulated** (`mock_model.py`); a live OpenAI-compatible route is wired in `model.py` but **not evaluated** |
| Course notes | **Sample notes written for this project**, not real module material |
| Model-based question interpretation, real course notes with embeddings, tutor review of reports, replay evaluation with seeded wrong answers (no participants) | **Planned** |

Known limits: the parser only recognises the notation in the examples (P(A), P(B), P(A∩B), P(A|B),
P(A∪B)); the app keeps one conversation in memory, so it is single-user; the word-overlap check in
`verify.py` can be fooled by a sentence that reuses the passage's words with a different meaning
(for example, a negation); values are read to six decimal places.

## Technology stack

- **Python 3 standard library only** (`http.server`, `json`, `re`, `urllib`). No packages to install.
- **Front end:** one `index.html` with plain JavaScript; no framework.
- **Retrieval:** the Lab 4 lexical scorer (weighted word overlap), extended with passage ids and
  currency reranking. Embedding retrieval is planned but undecided (it would need real notes first).
- **Language model:** `mock_model.py` by default. `model.py` can call any OpenAI-compatible chat
  endpoint through environment variables; which model to use is undecided and untested.
- **Tests and figures:** `unittest`; Playwright with headless Chrome for the screenshots
  (`scripts/`, only needed to regenerate figures); Pillow for the storyboards.

## Running or inspecting the work

```bash
python app.py                       # then open http://localhost:8000
python -m unittest discover -s tests -v
python retrieve.py --selftest
python tools.py --selftest
python mock_model.py --selftest
python checker.py "P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?"
python retrieve.py --no-rerank "can two events be mutually exclusive and independent"   # the Lab 4 ranking failure
```

Try the five example chips on the page. Tick **Demo: simulate an overconfident model reply** to see
the verifier remove unsupported sentences. Click **§ source** to highlight a passage. Click **This
source doesn't support it** to file a report; it is appended to `feedback_log.jsonl`.

Optional live model (not evaluated; use your own key and never commit it):

```bash
export IIS_MODEL=http IIS_MODEL_URL=https://.../v1/chat/completions IIS_MODEL_NAME=... IIS_API_KEY=...
python app.py
```

Regenerate figures (needs `pip install playwright pillow` and Chrome): start the app on port 8765,
then run `python scripts/frames.py docs/frames`, `python scripts/storyboards.py` and `python scripts/diagram.py`.
The figures were made on Linux; elsewhere set `CHROME` to your Chrome binary. The diagram PNG is the SVG
rendered in Chrome.

## Development record

**Phase 1 (Lab 1, `docs/phase1_literature/`).** The problem was framed as students overtrusting
fluent AI study answers. Five sources were verified. The gap was whether a one-click link to a
checked passage, added to a verbal uncertainty cue, helps students detect wrong STEM answers.

**Labs 2–3 (`docs/lab3_simulation/`).** This was a Markdown simulation with no running code. Test B
("Are they independent? I don't have the numbers.") showed the first design assumed facts the
student never gave. A topical source made that guess look verified. This led to two design
changes: show the interpretation, and gate the answer on missing information.

**Lab 4 (`docs/lab4_records/`).** The supplied starter app was used, because Lab 3 had no app.
Retrieval, provenance display and a confirmed tool were integrated. The test record found that
a superseded handbook passage ranked first.

**Who made these commits.** Commits `ddb6aee` to `4cf7da9` were generated by Claude in one session on
9 November 2026, which is why they fall within 14 minutes. I accepted its recommendations on scope (four
probability topics) and on simulating the language model. Later commits that contain code or text written by
Claude end with a `Co-Authored-By: Claude` line. In commits without it I made the edits myself; the
record below says where Claude advised.

**A2 changes (this repository):**

- [`ddb6aee`](../../commit/ddb6aee), [`6a8380d`](../../commit/6a8380d): imported the Lab 4 app and lab
  records as the baseline.
- [`40c192f`](../../commit/40c192f): replaced the course-admin corpus with probability notes. These
  include a superseded 2024 passage that states the Lab 3 over-generalisation. Superseded passages
  now rank last, which fixes the Lab 4 test-record failure. Checked with `--no-rerank` and a test.
- [`4391248`](../../commit/4391248): added the parser and the deterministic checker. The first rule
  lookup searched the whole corpus and matched the independence definition to a 2.4 sentence that
  only mentions independence. Lookup is now limited to the rule's section, and a test checks every rule.
- [`711ff31`](../../commit/711ff31): rebuilt the turn. Repair turns (clarify, correct, decline) now
  run before any model call. The model only words checked facts, and `verify.py` checks each
  sentence. The first version of the verifier removed correct definitions that are mostly formulas,
  so formulas now count as terms. Added the overclaim demo and the report-and-recheck path. Removed
  the Lab 4 image demo as out of scope.
- [`d4129b9`](../../commit/d4129b9): redesigned the page around the uncertainty cue and one-click
  sources. Screenshots showed the correction form was always open, because a CSS rule overrode
  `hidden`, and that the monospace font displayed ∩ as "n". Both were fixed.
- [`b4a8e25`](../../commit/b4a8e25): added the system diagram and storyboards made from real screens.
  Report wording was corrected after the screenshot showed it calling the student's values
  "calculation".

- 16 November, A1 revision (with Claude): after reviewing my A1 feedback, I decided to rebuild the
  report around the A1 question (when does optional, low-effort access to evidence help people rely
  appropriately on AI advice?). Claude proposed two changes, which this commit makes: each storyboard
  frame is now labelled implemented, fixed repair turn or simulated; and the planned user study in the
  system diagram became a replay evaluation without participants, as the module's examples use.
- **My own changes and checks (17 November):** I ran the app with the examples and my own inputs.
  Pasting a whole question into the P(A∩B) correction field made the server return NaN. The browser
  could not read the reply, so the old answer stayed on screen with only a technical "Error:" line
  added at the bottom of the card. I changed `from_fields` in `parse.py` to
  report "must be a number such as 0.2.", re-ran the 25 tests and retried the input (commit `b9c2676`,
  screenshot `docs/screenshots/fix_nonnumeric.png`).
- **Consistency fix after AI reviews (19 November, with Claude):** two AI reviews reported "checked"
  answers for impossible combinations (e.g. P(A|B) = 2). I reproduced one (`bug_conditional.png`) and
  chose to fix the code, not only the report. Claude drafted `check_values()` in `parse.py` for both
  input paths, plus six tests; I ran all 31 tests and retried the case (`fix_conditional.png`,
  [`ec28b79`](../../commit/ec28b79)). Not changed in code, and stated as limits in the report: a negated
  sentence can pass the word-overlap check, and superseded passages are still shown to the model.
- **My own wording fix (19 November):** while retesting, I noticed the message said "correct the values
  below" though the form is above it. I edited `app.py`, re-ran the tests and checked the page
  ([`f3bec15`](../../commit/f3bec15), `fix_wording.png`).
- **Second review round (19 November, with Claude):** reviews by OpenAI Codex and ChatGPT found more
  inputs still marked checked. I reproduced the worst: mutually exclusive events with P(A)=0.8 and
  P(B)=0.7 gave P(A∪B) = 1.5 (`bug_exclusive_union.png`). Claude drafted the fixes: P(A∩B) = 0 is
  applied in the checks, a given P(A∪B) or P(A|B) must match, negative, 1/0 and infinite values are
  rejected, rounded results are shown with ≈ and accepted by the verifier (a correct 0.3333 sentence
  had been removed), tiny probabilities are no longer read as zero, the form keeps "mutually
  exclusive" as a checkbox, and the cue now says what screening covers. It regenerated the storyboards,
  adding the student's triggering action to each, and the diagram. I ran all 44 tests and retried
  three cases in the browser ([`b2b9ce8`](../../commit/b2b9ce8), `fix_exclusive_union.png`). A negated
  sentence can still pass the word-overlap screen; the report states this limit.

All 44 tests pass on the tagged version (`python -m unittest discover -s tests`).

## AI assistance

- **Labs 1–3:** AI summaries of verified abstracts were checked sentence by sentence
  (`docs/phase1_literature/04_summary_checks.md`). OpenAI Codex drafted the Lab 3 simulation; the
  prompt log records what was kept and changed (`docs/lab3_simulation/02_PROMPT_LOG.md`).
- **A2:** Claude (Anthropic, Claude Opus 5.5, used through claude.ai) was asked to extend the Lab 4 app
  into the Labs 1–3 design, write the tests, capture screenshots, draw the diagram, and draft this
  README and the report. It was given the Lab 1–4 files, the A2 brief and the Week 1–5 slides.
- **A2 revision (16 November):** Claude was given my A1 report and its feedback, the A2 brief and
  rubric, the Week 1–4 lecture slides and this repository. It proposed the replay evaluation and the
  storyboard status labels, and drafted the revised report and this record.
- **Review response (19 November):** Claude checked which bugs in two AI reviews were real on
  `v1.1-a2`, and drafted the consistency check, its tests, these entries and the messages of
  `ec28b79` and `f3bec15`.
- **Second review response (19 November):** OpenAI Codex and ChatGPT were used only to review the
  submission. Claude reproduced their cases on `v1.2-a2`, drafted the fixes and tests, regenerated the
  figures, cropped the browser bar from `fix_nonnumeric.png`, and drafted these entries and the messages
  of `b2b9ce8` and this README commit.
- **What Claude checked:** it ran the test suite and self-tests and inspected every screenshot (this is
  how the hidden-form, ∩-glyph and wording bugs were found). It recomputed the example arithmetic and
  checked the references against the Lab 1 shortlist and the A1 sources.
- **What I checked or changed:** I found the NaN bug above while testing. Claude diagnosed the cause and
  told me which lines to change; I made the edit, tested it in the browser and committed it myself.
  For the consistency fix I reproduced the bug first, then ran and retried Claude's change; the
  wording fix was my own. In the second round I reproduced the 1.5 case, then retried it, a rounded
  P(A|B) and the form's checkbox after the fix.

## Additional files

- `docs/phase1_literature/`: Lab 1 search plan, shortlist, summary checks, related-work map.
- `docs/lab3_simulation/`: Lab 3 specification, traces, prompt log, storyboards and system path (SVG).
- `docs/lab4_records/`: Lab 4 context map, test record, screenshots and tool log.
- `docs/lab4_handouts/`: the supplied Lab 4 instructions, kept for traceability.
- `docs/diagram/`, `docs/storyboards/`, `docs/frames/`, `docs/screenshots/`: report figures and their sources.
- No ZIP is needed; everything is in the repository.
