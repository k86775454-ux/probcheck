"""Simulated language model, so the app runs with no key and no network.

    python mock_model.py --selftest

The mock reads the checked facts that app.py placed in the context and words each one as a
sentence that cites its passage, as the instructions ask a live model to do. It is a simulation:
its wording is fixed, so it cannot show how a real model would paraphrase or drift.

overclaim=True (the "Simulate an overconfident model" switch) adds two sentences of the kind a
fluent model produces: the over-generalised rule from the superseded 2024 notes (the Lab 3 Test B
error) and an uncited extra claim. verify.py must catch both.
IIS_MOCK_BREAK=1 returns malformed text, to test the fallback.
"""
import json
import os
import sys

OVERCLAIMS = [
    {"text": "So mutually exclusive events are always dependent, so they can never be independent.",
     "passage_id": "n23_independence_2024#1"},
    {"text": "This result holds for any pair of events you will meet in the course, whatever "
             "their probabilities are, with a 95% guarantee.", "passage_id": None},
]


def call(messages, schema=None, overclaim=False):
    if os.environ.get("IIS_MOCK_BREAK"):
        return "Sure! Here is your answer: they are not independent."
    facts = []
    for m in messages:
        if m["content"].startswith("CHECKED FACTS"):
            facts = json.loads(m["content"].split("\n", 1)[1])
    sentences = [{"text": f["text"], "passage_id": f["support"]} for f in facts]
    if overclaim:
        sentences += OVERCLAIMS
    return json.dumps({"sentences": sentences})


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        msg = [{"role": "user", "content": "CHECKED FACTS\n" + json.dumps(
            [{"text": "Independence means P(A∩B) = P(A)P(B).", "support": "n23_independence#1"}])}]
        assert json.loads(call(msg))["sentences"][0]["passage_id"] == "n23_independence#1"
        assert len(json.loads(call(msg, overclaim=True))["sentences"]) == 3
        print("ok: mock words checked facts; overclaim adds 2 sentences")
