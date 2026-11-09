# 01_SPEC.md: use case and system path

**Project:** Evidence-checking study assistant

**Selected use case:** Check whether a short probability explanation is supported by the course definitions, then let the student inspect or report a mismatch. This extends the Lab 2 normal and failure-recovery storyboards and addresses the Lab 1 concern that students may overtrust fluent AI answers when uncertainty and evidence are hard to judge.

**Route:** Structured Markdown simulation. All model, retrieval and checking operations below are simulated; no live model or course database was connected.

## User goal

A first-year student wants to understand whether mutually exclusive events can also be independent, and wants a way to verify the explanation against course material before relying on it.

## System inputs

- Student question: “Can two events be mutually exclusive and independent?”
- Course context: two provided definitions (mutual exclusivity means `P(A∩B)=0`; independence means `P(A∩B)=P(A)P(B)`).
- For the problem case, the student gives an incomplete question and no probabilities: “Are they independent? I don't have the numbers.”

The course definitions are mock retrieved passages written into this simulation; they are not quoted from an actual course database.

## Processing and technology

1. **Input capture (planned UI):** receive the question and optional event probabilities.
2. **Retrieval (simulated):** return the two course definitions above, with source labels “Course notes — Mutual exclusivity” and “Course notes — Independence”.
3. **Claim and condition check (simulated):** compare the definitions. If both events have positive probability, mutual exclusivity gives an intersection of zero while independence requires the product of positive probabilities, so both properties cannot hold. If probabilities are missing, the system must not assume they are positive.
4. **Response (simulated):** state the conditional conclusion, show the definitions as evidence, and provide “View source”, “Correct these details”, and “This source doesn't support the answer” actions.

No particular language model or retrieval software is implemented. A future implementation would need course-approved retrieval, source-to-claim matching, and deterministic arithmetic/condition validation around any generated explanation.

## Intended result and next action

The student sees a concise answer, the condition it depends on, and the supporting definitions. They can inspect a source, correct the event details, report an evidence mismatch, or ask a follow-up. They decide whether to use the explanation.

## Fallback strategy

When event probabilities or other necessary conditions are missing, ask for them or explain the conditional result; do not silently presume positive probabilities. If retrieval is empty, conflicting, or unavailable, say the answer has not been checked against course material and offer a retry or an unverified general explanation. A mismatch report triggers a recheck and correction; it does not automatically train the model.

## System path or interaction diagram

See [06_system_path.svg](06_system_path.svg). It labels the current Markdown simulation separately from planned components.

## Test A: standard input

**Input:** “Can two events be mutually exclusive and independent? Let `P(A)=0.4` and `P(B)=0.5`.”

**What the system receives:** The question, two positive probabilities, and the simulated course definitions of mutual exclusivity and independence.

**What it does:** Simulated retrieval returns both definitions. The condition check calculates `P(A)P(B)=0.2`; mutual exclusivity requires `P(A∩B)=0`, whereas independence would require `P(A∩B)=0.2`. The requirements conflict.

**Response and next action:** “With these probabilities, the events cannot be both mutually exclusive and independent. Mutual exclusivity requires `P(A∩B)=0`; independence requires `P(A∩B)=0.4×0.5=0.2`. These retrieved definitions support that conclusion. View the two source entries, correct the probabilities, or ask a follow-up.” The student can inspect the sources and choose whether to rely on the explanation.

## Test B: problem input

This test extends the evidence-mismatch problem identified in the Week 2 storyboard by examining how an ambiguous question can lead to an unsupported assumption.

### First run

**Input:** “Are they independent? I don't have the numbers.” No earlier event descriptions are available in this test.

**What the system receives:** An ambiguous reference (“they”), no event definitions or probabilities, and the same simulated course definitions.

**What it does:** Simulated retrieval returns the two general definitions. The first-pass response generator overgeneralises from the Lab 2 example and assumes that the question concerns mutually exclusive events with positive probabilities. This assumption is not supported by the input.

**Response and next action:** First-pass response: “If they are mutually exclusive, they are not independent.” It shows the two definitions and a “This source doesn't support the answer” action. The student can report the mismatch, but the response does not make its assumption visible.

**Problem found:** The definitions alone do not establish that these particular events are mutually exclusive, and no probabilities were given. A topical source link can make an unsupported assumption look verified. The person needs an explicit way to see and correct what the system inferred. The initial response also omits the positive-probability condition, making its generalisation mathematically incorrect when an event has probability zero.

## Review and revision

| Review question | Evidence and problem found |
|---|---|
| Did it show what it understood? | Test B first run returned a conclusion without showing the assumed event relationship or positive-probability condition. |
| Did it ask for missing information instead of guessing? | No. It inferred mutual exclusivity from context despite the question not saying so. |
| Could the person correct a wrong extraction or decision? | A mismatch report existed, following the Lab 2 recovery storyboard, but there was no direct way to inspect or edit the system's inferred details. |
| Did it keep the person in control? | It offered a report action, but presented the unqualified conclusion before asking the student to confirm the assumption. |
| Did it respond honestly about evidence? | The retrieved definitions are relevant, but by themselves they cannot support a claim about unspecified events. The response overstated what had been checked. |

### Changes made

- **Interaction change:** show the system's interpretation and condition, then ask a focused clarification with choices: “Are you asking about mutually exclusive events? If so, do you know whether both have positive probability?” Provide “Neither / not sure” and “Correct my question” options. Keep source inspection and mismatch reporting available.
- **System change:** add a pre-response validation gate. The simulated checker may state the conditional theorem, but it cannot apply it to the student's events unless mutual exclusivity is confirmed or present in the input. It must request missing probabilities when the student's question depends on them. Source retrieval is displayed as context, not proof that the specific claim was verified.

### Revised Test B

**Input:** “Are they independent? I don't have the numbers.”

**What the system receives:** Same ambiguous question and simulated definitions; no event identities, relationship, or probabilities.

**What it does:** The validation gate detects that “they” has no referent and that the information needed for a case-specific conclusion is absent. It does not classify the events. It presents the definition passages as general context and asks for clarification.

**Response and next action:** “I can't tell which events you mean yet. Are you asking whether *mutually exclusive* events can also be independent? **If yes**, the answer depends on their probabilities: when both are greater than zero, they cannot be both; if either has probability zero, they can be independent. **If not sure**, tell me what the two events are, or choose ‘Correct my question’. The definitions below are general course notes; I have not checked them against your specific events. You can view the sources or report a mismatch.” The student can clarify, correct the question, view a source, or stop without accepting a guess.

### Why the changes help

The clarification makes the system's uncertain interpretation visible and gives the student a low-effort way to correct it. The validation gate prevents a general definition from being presented as evidence about unspecified events, while the conditional explanation still teaches something useful without inventing probabilities. Retrieval remains simulated; this revised path has not been tested with live course materials or users.

## Implementation status and limits

- **Implemented in this submission:** written system specification, two reproducible Markdown test traces, revision and exported SVG system path; Lab 2 normal and failure-recovery storyboards are included for context.
- **Simulated:** retrieval, inference, condition validation and responses in Tests A and B.
- **Planned:** interactive UI, real course-material indexing, source passage matching, model/tool integration and user study.
- This exercise demonstrates a plausible interaction path; it does not establish that a real model or retrieval system will behave this way.
