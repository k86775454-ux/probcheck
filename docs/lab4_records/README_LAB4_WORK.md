# Lab 4 integration — evidence-checking study assistant

This is the **complete runnable Lab 4 app route** built from the official `lab4_pack/` starter. The prior Lab 3 submission was a Markdown-only simulation and did not contain a runnable app, so the supplied Lab 4 app was used as the common starting point, as permitted by the handout. The UI title carries forward the prior project idea; the corpus and test examples remain the instructor-supplied demonstration material.

## Run it

From this folder (Python 3, standard library only):

```bash
python app.py
```

Keep that terminal open, then visit <http://localhost:8000/> in a normal browser. The default **mock** mode requires no API key or network.

## Browser exercises

1. **Grounded question:** Click `Grounded question`. Check the answer and three evidence entries with source, section, update date and score.
2. **Stale source:** Click `Stale source`. Confirm the older source is labelled SUPERSEDED and the displayed answer uses the 2026–27 passage.
3. **Unanswerable:** Click `Unanswerable`. Check that the app gives no unreliable evidence and suggests consulting the module lead.
4. **Tool:** Click `Propose revision slot`, read the date and duration, then click `Confirm`. Check the result, `schedule.json` and `tool_log.jsonl`. Click `Test invalid 900-minute call` to verify refusal without executing the tool.
5. **Image:** Click `Test poster image` to view the confidence and `Test noticeboard image` to view the refusal and reason.

Run the starter checks:

```bash
python retrieve.py --selftest
python tools.py --selftest
python vlm.py --selftest
python -m unittest discover -s tests -v
```

## Files for submission

- `app.py`, `index.html`, `model.py`, `mock_model.py`, `retrieve.py`, `tools.py`, `vlm.py` — integrated project code.
- `corpus/`, `sample_images/`, `recorded_runs/` — supplied corpus, VLM examples, and mock replies.
- `01_CONTEXT_MAP.md`, `02_TEST_RECORD.md`, `tool_log.jsonl` — required work and real observed test outcomes.
- `schedule.json` — generated on the first successful Confirm; intentionally not pre-populated so the first browser test visibly adds a slot. `tests/schedule_after_confirmation.json` preserves the recorded schedule from the original completed test. No external calendar is modified.
- `tests/` — automated regression tests and rendered UI screenshots.
- Original Lab 4 handouts and documentation are retained for traceability.

**Important:** This corpus is a fictitious lab example. The November deadline and late policy shown in it are not verified current University of Birmingham module rules. The mock image score is a fixed example output, not measured model reliability. For a live model, review tool permissions, prompt-injection resistance and evidence validation before deployment.
