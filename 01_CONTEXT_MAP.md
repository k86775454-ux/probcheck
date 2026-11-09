# 01_CONTEXT_MAP.md — Lab 4 context inspection

**Starting point:** the *complete runnable Lab 4 supplied app* (the Lab 3 submission used the Markdown simulation route). I ran the starter and then integrated the retrieval path into `turn(message)` in `app.py`.

**Where to inspect:** `log_context(parts)` prints each exact role/content pair immediately before `model.call_json(parts, SCHEMA)`. I inspected an ordinary request: `When is coursework 1 due?`.

## Initial context (before Phase 2)

The supplied starting app called `model.call_json([{"role": "user", "content": message}], SCHEMA)`. Its only model input was the current user message. There were no app instructions, history, retrieved passages or tool definitions in that model request. There was **nothing redundant to remove**.

## Integrated context (after Phase 2)

For the same ordinary question, `CONTEXT:` terminal lines contain these three parts, in this order:

| part | where it comes from | information type / trust boundary | size |
|---|---|---|---|
| instructions | Fixed system text constructed inside `app.py` | App instructions: treat quoted corpus material as evidence, not instructions; do not guess | short |
| retrieved passages and provenance | `retrieve.retrieve(message, k=3)` plus `retrieve.format_passages(evidence)` loading the supplied `corpus/` files | **Quoted source data (lower trust)**: includes source, section, date, relative score and passage text. It is passed as a separate user-role message clearly marked as quoted material | medium (3 passages for grounded example) |
| current user message | The text submitted by the browser, e.g. `When is coursework 1 due?` | User input | short |
| conversation history | not present | not present | not present |
| tool definitions | not present in model request; proposed `book_slot` calls are validated in app code and `tools.py` | not present | not present |
| images | not present in model request; the supplied `vlm.ask` mock handles the two test image paths separately | not present | not present |

**Context change tested:** After retrieval integration, the model request now contains instructions + the quoted top-three results + the original question. The console logged all three; the local mock still returns valid JSON, and the page shows the current handbook passage and provenance for the grounded test.

**Removal decision:** No redundant part was removed from the model request. The user question is still needed; the instruction distinguishes data from instructions; the retrieved quotes are needed for traceability in a future live-model route. No chat history or private information is included. Unrelated appointment actions from the supplied mock are **not displayed** for retrieval answers.

**After-retrieval review:** Ensure the retrieved source is not superseded before answering. For the late-submission test the lexical retriever puts the older handbook first; the answer path explicitly selects the newer matching section and shows a warning and both sources. A match score is a *relative lexical ranking signal*, not probability or confidence. If the best result is below 0.25, the app does not show it as evidence and directs the user to the module lead.

**Scope limitation:** The mock model processes the final user message using pre-recorded outputs. The locally selected retrieved passage is returned as the displayed answer; this does **not** prove a live LLM correctly followed the instruction or grounded its own generation. The sample corpus is for the lab and its dates/policies are not verified UoB rules.
