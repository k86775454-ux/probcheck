# Testing record for v1.4-a2 and v1.5-a2

The README's development record summarises these rounds; this file keeps the full detail. Each case
was reproduced before it was fixed, and each fix has a regression test. The harnesses are in
`scripts/wide_tests/` (see the README, "Running or inspecting the work").

## Rounds before v1.4-a2 (commit `daa9f67`)

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
  and B are declined, a feasibility test (`_possible` in `parse.py`) rejects values that no two
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
  and pushed it (tag [`v1.4-a2`](../../../tree/v1.4-a2)).

## Final check before v1.5-a2

- **Final independent check (20 November, with Claude):** I had OpenAI Codex check the submitted
  `v1.4-a2` again: the PDF, the Overleaf files and the repository. It judged the submission ready and
  found three narrow gaps, which Claude reproduced on `daa9f67`:
  - "Are I and B independent?" and "Is A independent of P?" were answered about A and B (14 of its
    1,387 targeted cases). The parser left out "I" and "P" so as not to read the pronoun or the
    notation as events, and so missed them in phrases where only an event fits.
  - A stated "A and B are dependent" was not checked against values that are independent
    (P(A∪B) = 0.58 was shown as checked).
  - Resubmitting the correction form dropped a stated "not independent", so a rejected question
    became "checked" (the README stated this limit, but the behaviour still changed the question).

  It also found "an feasibility test" in the README. The fixes:
  - "I" and "P" are read as events in phrases where only an event fits (`EVENT_PHRASES` in
    `parse.py`): "Are I and B ...", "I and B are ...", "independent of P", "event P", "the
    probability of I or B". "I think ..." and "find P" are still not events.
  - A stated "dependent" counts as "not independent", and "not dependent" as "independent". Asked
    ("Are A and B dependent?", "Is A dependent on B?") it stays the question.
  - The correction form shows a stated "not ..." as a ticked box, keeps it when resubmitted, and drops
    it only if the student unticks it. Ticking both "independent" and "not independent" is reported.
  - A question about events other than A and B is now declined before its values are checked.

  Three tests cover the cases (`tests/test_review_round5.py`), and the phrasing harness now includes
  "dependent" premises. The final runs found no failures in the cases they generate:

  | Test | Cases |
  |---|---|
  | `harness_grid.py`, two seeds | about 21,000 questions and forms each |
  | `harness_premises.py`, two seeds | 50,000 questions and form resubmissions each |
  | `harness_phrasing.py`, two seeds | about 18,000 phrasings each, compared with the form |
  | `stress_values.py`, two seeds | 100,000 value sets each, against an exact rational oracle |
  | `http_requests.py` | odd requests and 400 random multi-turn sequences |
  | `browser_flows.py` | every page flow in headless Chrome, including the kept "not ..." box |
  | `unittest` | 82 tests |
