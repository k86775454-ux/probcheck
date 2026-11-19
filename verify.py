"""Check every sentence the model wrote before it reaches the screen.

A schema guarantees shape, not truth (Lecture 09), so each sentence is checked in code:
  1. it points to a passage that is shown on the page;
  2. that passage is current, not superseded;
  3. every number in it comes from the student's values, the calculation, or the passage
     (a calculated number may appear rounded to four decimals, as the page shows it);
  4. enough of its wording appears in that passage.
A sentence that fails is removed and listed with the reason, never shown as part of the answer.
These checks screen support; they do not prove the meaning: a sentence that reuses a passage's
words with the opposite meaning (for example, a negation) can still pass.
"""
import math
import re

STOP = set("a an and are as at be because both but by can cannot for from has have here if in is it "
           "its of on or so than that the then there these they this to was while with".split())


def numbers_in(text):
    # ignore section numbers such as 2.3 when they follow the word "section"
    text = re.sub(r"section\s+\d+(\.\d+)*", " ", text, flags=re.I)
    return [float(x) for x in re.findall(r"(?<![A-Za-z])\d*\.?\d+(?:e-?\d+)?", text)]


def number_allowed(n, allowed):
    """Exact match, or the four-decimal rounding the page uses for calculated values."""
    return any(math.isclose(n, a, rel_tol=1e-9, abs_tol=1e-12) or abs(n - round(a, 4)) < 1e-9
               for a in allowed)


def content_words(text):
    """Words of three or more letters, plus formulas such as P(A∩B) or P(A)P(B) as single terms,
    because in these notes the formula often carries the claim."""
    formulas = {f.replace(" ", "") for f in re.findall(r"(?:P\s*\([^)]*\)\s*)+", text)}
    words = re.sub(r"(?:P\s*\([^)]*\)\s*)+", " ", text).lower()
    return {w for w in re.findall(r"[a-z]{3,}", words) if w not in STOP} | formulas


def check_sentence(sentence, evidence_by_id, allowed_numbers):
    """Return (ok, reason, matched_terms)."""
    pid = sentence.get("passage_id")
    if not pid or pid not in evidence_by_id:
        return False, "it does not point to a passage shown on this page", []
    passage = evidence_by_id[pid]
    if passage.get("superseded"):
        return False, "it relies on superseded notes (%s)" % passage["source"], []
    allowed = list(allowed_numbers) + numbers_in(passage["text"]) + [0.0, 1.0]
    for n in numbers_in(sentence.get("text", "")):
        if not number_allowed(n, allowed):
            return False, "the number %g is not in your values, the calculation or the passage" % n, []
    matched = sorted(content_words(sentence.get("text", "")) & content_words(passage["text"]))
    if len(matched) < 2:
        return False, "too little of it appears in the passage it cites", matched
    return True, "", matched


def verify(sentences, evidence, allowed_numbers):
    by_id = {e["id"]: e for e in evidence}
    shown, removed = [], []
    for s in sentences if isinstance(sentences, list) else []:
        if not isinstance(s, dict) or not isinstance(s.get("text"), str):
            continue
        ok, why, matched = check_sentence(s, by_id, allowed_numbers)
        item = {"text": s["text"], "passage_id": s.get("passage_id"), "matched": matched}
        if ok:
            shown.append(item)
        else:
            item["why"] = why
            removed.append(item)
    return shown, removed


def recheck(sentence, evidence, steps, allowed_numbers):
    """Run when a student reports a mismatch: say exactly which part the notes support."""
    by_id = {e["id"]: e for e in evidence}
    ok, why, matched = check_sentence(sentence, by_id, allowed_numbers)
    passage = by_id.get(sentence.get("passage_id"))
    in_passage = numbers_in(passage["text"]) if passage else []
    from_calc = [n for n in numbers_in(sentence["text"]) if not any(abs(n - p) < 1e-6 for p in in_passage)]
    return {"supported": ok, "reason": why, "matched_terms": matched,
            "numbers_from_calculation": sorted(set(from_calc)), "steps": steps if from_calc else []}
