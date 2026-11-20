# ProbCheck: an evidence-checking study assistant for probability

Intelligent Interactive Systems · A2 project · student 3098204
README prose: about 3,050 words (code blocks and commands not counted).

ProbCheck helps a first-year student decide whether to trust an explanation of a probability
question. Each sentence of the answer links to the course-note passage it relies on. Numbers are
recalculated in code. A verbal cue says how far the answer was checked. When the question is
ambiguous, the system asks instead of guessing.

**Submitted version:** tag `v1.4-a2` (commit hash on the report's first page). Earlier tags: `v1.0-a2` (9 November baseline), `v1.1-a2` (17 November), `v1.2-a2` and `v1.3-a2` (19 November).

## Project status

| Part | Status |
|---|---|
| Question parsing with a visible, editable interpretation (`parse.py`) | Implemented (rule-based) |
| Gate: clarify unclear events, reject impossible or inconsistent values (typed question and correction form; a stated "mutually exclusive" or "independent" is applied, and a stated "not ..." is checked; a feasibility test rejects value sets that no two events can have), decline out-of-scope questions and events other than A and B | Implemented |
| Deterministic checks: independence, mutually exclusive + independent, whether A and B are mutually exclusive, addition rule, P(A∩B), conditional probability; a value that follows from the givens is derived and its step shown (`checker.py`) | Implemented |
| Retrieval with source, section, date, score; superseded passages ranked last and labelled (`retrieve.py`) | Implemented |
| Per-sentence screening of the model's wording: citation, current source, allowed numbers, word overlap (`verify.py`) | Implemented; does not check that the meaning is correct |
| Page: uncertainty cue ("Screened against the notes" states what the screening covers), one-click source highlight, correction form with every value field and checkboxes for a stated "mutually exclusive" or "independent", mismatch report, removed-sentence list | Implemented |
| Revision-slot tool with validation, confirmation and log (`tools.py`) | Implemented (carried over from Lab 4, now with a topic) |
| Language model that words the checked facts | **Simulated** (`mock_model.py`); a live OpenAI-compatible route is wired in `model.py` but **not evaluated** |
| Course notes | **Sample notes written for this project**, not real module material |
| Model-based question interpretation, real course notes with embeddings, tutor review of reports, replay evaluation with seeded wrong answers (no participants) | **Planned** |

Known limits: the parser only recognises the five quantities P(A), P(B), P(A∩B), P(A|B) and
P(A∪B), in common notations, and simple phrasings ("not mutually exclusive" is read; other ways of
negating may not be); complements and P(B|A) are declined rather than answered; the app keeps one
conversation in memory, so it is single-user; the word-overlap check in `verify.py` can be fooled by
a sentence that reuses the passage's words with a different meaning (for example, a negation).
P(A), P(B) and P(A∩B) are taken exactly as typed, so 0.1667 typed for 1/6 is not equal to 1/6 (the
page then shows both with more decimals and suggests typing the fraction). A typed P(A∪B) or P(A|B)
may be off by half a unit in its last digit, at most 0.0005, so 0.6667 can stand for 2/3; if that
puts a worked-out P(A∩B) just outside its range, the nearest possible value is used and the step
says so. Positive probabilities below 0.000000001 are declined. The correction form has no field
for a stated "not ...", so resubmitting the form leaves it out.

## Technology stack

- **Python 3 standard library only** (`http.server`, `json`, `re`, `urllib`). No packages to install.
- **Front end:** one `index.html` with plain JavaScript; no framework.
- **Retrieval:** the Lab 4 lexical scorer (weighted word overlap), extended with passage ids and
  currency reranking. Embedding retrieval is planned but undecided (it would need real notes first).
- **Language model:** `mock_model.py` by default. `model.py` can call any OpenAI-compatible chat
  endpoint through environment variables; which model to use is undecided and untested.
- **Tests and figures:** `unittest`; Playwright with headless Chrome for the screenshots
  (`scripts/`, only needed to regenerate figures); Pillow for the storyboards. The wider test
  harnesses in `scripts/wide_tests/` use NumPy and Python's exact fractions for their ground truth; the app
  itself does not.

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

Wider tests (optional, need `pip install numpy`; each takes a few minutes and prints its
failures; `SEED=n` before a harness tries other random cases):

```bash
python scripts/wide_tests/harness_grid.py .        # value grid, random forms, demo, phrasings, odd inputs
python scripts/wide_tests/harness_premises.py .    # stated premises, fractions and percentages, form resubmission
python scripts/wide_tests/harness_phrasing.py .    # phrasings, notation and number formats, compared with the form
python scripts/wide_tests/stress_values.py . 1 100000   # value sets against an exact feasibility test
# with a server running from a scratch copy (python app.py --port 8766):
python scripts/wide_tests/http_requests.py 8766    # odd requests and random multi-turn sequences
python scripts/wide_tests/browser_flows.py http://localhost:8766/   # every page flow in headless Chrome
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
- **Third review round (20 November, with Claude):** further AI reviews (including OpenAI Codex and
  ChatGPT) found that "not mutually exclusive" was read as mutually exclusive, so P(A∪B) = 0.9 was shown
  as checked; that a stated "mutually exclusive" was not used for P(A|B); that the correction form had
  no P(A∪B) or P(A|B) field, so resubmitting it dropped a value that contradicted the others; that
  fractions were rounded, so 1/3 × 1/2 was "not equal" to 1/6; that "What is P(A∩B)?" and "Are A and B
  mutually exclusive?" with numbers were misread; that a stated "independent" was ignored; and that very
  small numbers were removed from correct sentences. One claim, a missing § sign, was a false alarm.
  This time I asked Claude to do the reproduction as well: it reproduced the cases on `v1.3-a2`,
  captured the before and after screens (`bug_not_exclusive.png`, `fix_not_exclusive.png`), drafted the
  fixes and tests, and re-captured the changed storyboard frame.
- **Wider testing before v1.4 (20 November, with Claude):** before pushing these fixes I asked Claude
  to test many more cases, fix anything it found, and keep the code readable, reliable and accurate.
  It wrote the harnesses in `scripts/wide_tests/`, which compare ProbCheck with a ground truth it does
  not share: a linear-programming feasibility test (in SciPy at first), and the correction form filled
  in with the true reading of each question. A full run covers over 100,000 questions and form
  submissions and 100,000 random value sets. The wider testing found more: "A and B are independent.
  Are they mutually exclusive?" was answered as an independence question; "the probability of A or B,
  given P(A)=…" was answered as P(A|B); "Are A and C independent?" was answered about A and B;
  "dependent" and lowercase notation were not read; impossible values such as P(A∩B) = 0.7 with P(A∪B)
  = 0.2 were accepted, while 0.6667 typed for 2/3 was rejected; and 0.1667 typed for 1/6 produced
  "0.1667 ≠ 0.1667". Claude fixed these: the question asked now decides the type, events other than A
  and B are declined, an feasibility test (`_possible` in `parse.py`) rejects values that no two
  events can have, and close values are shown with enough decimals to differ. Tests cover both rounds
  (`tests/test_review_round3.py`, `tests/test_wider_checks.py`).
- **Second wider pass (20 November, with Claude):** I then asked for another large round of testing.
  Claude fuzzed the notation and number formats, sent odd requests and random multi-turn sequences to
  a running server, drove every page flow in headless Chrome (`http_requests.py`, `browser_flows.py`),
  and reran the harnesses with new random seeds. It found that "P(A)=0,3" was read as 0, so all-zero
  values were "checked: independent"; that "30 percent", "equals", "1e-3", "Pr(A)", "P(A ⋂ B)" and
  "P(A∩B)=?" were not read or were misread; that a value given twice with different numbers was
  silently resolved; that P(A') and P(B|A) were ignored rather than declined; that "P(A)=0.3. What is
  P(A|B)?" was shown as checked with no answer; that P(A) = 0 or 1 was not used, so "P(A)=0, P(B)=0.5.
  Are A and B independent?" asked for P(A∩B); that P(B) = 0 did not make P(A|B) undefined until
  P(A∩B) was given; and that a malformed request could drop the connection. Claude fixed these, and
  ten tests cover them (`tests/test_more_inputs.py`).
- **Fourth review round (20 November, with Claude):** before pushing, I had OpenAI Codex review the
  first v1.4 patch independently and gave its report to Claude. From about 37,000 checks it reported
  nine kinds of problem, including 214 impossible value sets that were accepted. Claude reproduced
  them on the current patch: three were already fixed by the second pass ("1e-3", a value given twice,
  the slot message), and six were not. "P(A)=0, P(A|B)=0.5" was checked as 0.5: the feasibility test
  stood in a tiny positive number for "P(B) > 0", and its tolerance let the contradiction through.
  Rounded values could give P(A|B) = −0.0002 or 1.0002. Tiny probabilities were rounded away
  (10^-14 became 0, and 10^-16 counted as equal to 0). "Are C and D independent?" and "Is A
  independent of C?" were answered about A and B. Without a question mark, "Are A and B mutually
  exclusive" was read as a premise. "P(A)=0.5/2" was read as 0.5, and a stated "not independent" was
  never checked against the values. Claude's own test oracle had the same blind spot, because it
  also used floating-point tolerances with P(B) ≥ 10^-9, so it was replaced by an exact one using
  fractions. The fixes:
  - P(B) > 0 is now tested exactly.
  - The rounding allowance for P(A∪B) and P(A|B) now follows the digits typed, and a worked-out value
    that rounding puts just outside its range is moved to the nearest possible value, with the step
    saying so.
  - Floating-point noise is removed relative to the numbers involved.
  - Every event name in the question is read.
  - Word order marks a question.
  - A number is read whole or reported.
  - A stated "not ..." is checked.
  - Slots for different topics on one day are both kept.

  Nine tests cover the cases (`tests/test_review_round4.py`). The final runs of every harness (two
  random seeds each), the HTTP test and the browser test found no failures. The review's own claim
  still stands: "no failures" covers the cases these tests generate, not every possible input. I
  applied the third-round, wider-testing and fourth-round changes as one commit, ran all 79 tests
  and pushed it (tag [`v1.4-a2`](../../tree/v1.4-a2)).

All 79 tests pass on the tagged version (`python -m unittest discover -s tests`).

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
- **Third and fourth review responses and wider testing (20 November):** at my request Claude
  reproduced the reported cases on `v1.3-a2`, captured the before and after screenshots, wrote the
  wider test harnesses and the HTTP and browser tests, drafted the fixes, tests, this entry and the
  commit message, re-captured the changed storyboard frame, and added an archive note to the Lab 4
  record.
- **What Claude checked:** it ran the test suite and self-tests and inspected every screenshot (this is
  how the hidden-form, ∩-glyph and wording bugs were found). It recomputed the example arithmetic and
  checked the references against the Lab 1 shortlist and the A1 sources.
- **What I checked or changed:** I found the NaN bug above while testing. Claude diagnosed the cause and
  told me which lines to change; I made the edit, tested it in the browser and committed it myself.
  For the consistency fix I reproduced the bug first, then ran and retried Claude's change; the
  wording fix was my own. In the second round I reproduced the 1.5 case, then retried it, a rounded
  P(A|B) and the form's checkbox after the fix. In the third round I decided to fix the code rather
  than narrow the report's claims, asked Claude to reproduce the cases and capture the screenshots,
  and required wider testing, and then a second large round, before anything was pushed. I then
  had OpenAI Codex review the patch independently and passed its report to Claude. I applied the
  change, ran the tests, and committed and pushed it.

## Additional files

- `docs/phase1_literature/`: Lab 1 search plan, shortlist, summary checks, related-work map.
- `docs/lab3_simulation/`: Lab 3 specification, traces, prompt log, storyboards and system path (SVG).
- `docs/lab4_records/`: Lab 4 context map, test record, screenshots and tool log.
- `docs/lab4_handouts/`: the supplied Lab 4 instructions, kept for traceability.
- `docs/diagram/`, `docs/storyboards/`, `docs/frames/`, `docs/screenshots/`: report figures and their sources.
- No ZIP is needed; everything is in the repository.
