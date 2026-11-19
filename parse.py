"""Turn a student's question into an interpretation the student can see and correct.

    python parse.py "Are they independent? I don't have the numbers."

The interpretation is an inference about what the student meant, so it is always shown on the page
and can be edited (Correct these details). Nothing here decides the answer: it only reads the
question type, which events are meant and which probabilities were given, and lists problems.
"""
import json
import re
import sys

NUM = r"(\d+(?:\.\d+)?\s*%|\d+\s*/\s*\d+|\d*\.\d+|\d+)"
JOINT = r"P\s*\(\s*A\s*(?:∩|n|and|&|∧|,)\s*B\s*\)|P\s*\(\s*AB\s*\)"
COND = r"P\s*\(\s*A\s*\|\s*B\s*\)"
UNION = r"P\s*\(\s*A\s*(?:∪|u|or|∨)\s*B\s*\)"
SINGLE = {"P(A)": r"P\s*\(\s*A\s*\)", "P(B)": r"P\s*\(\s*B\s*\)"}
PRONOUN = r"\b(they|them|these|those|it|this one|both)\b"

TYPES = {
    "exclusive_and_independent": "Can mutually exclusive events also be independent?",
    "independence": "Are A and B independent?",
    "conditional": "What is P(A|B)?",
    "union": "What is P(A∪B)?",
    "exclusive": "What does mutually exclusive mean?",
    "other": "Something the notes may not cover",
}


def _value(text):
    text = text.replace(" ", "")
    if text.endswith("%"):
        return float(text[:-1]) / 100
    if "/" in text:
        a, b = text.split("/")
        return float(a) / float(b) if float(b) else float("nan")
    return float(text)


def _grab(pattern, text):
    """Return (value, text with the match removed) for 'pattern = number'."""
    m = re.search("(%s)\\s*(?:=|is|:)\\s*%s" % (pattern, NUM), text, flags=re.I)
    if not m:
        return None, text
    return _value(m.group(2)), text[:m.start()] + " " + text[m.end():]


def check_values(values, exclusive=False):
    """Problems with the numbers themselves, shared by the question parser and the correction form.

    Each value must lie in [0, 1], and the values must fit together: P(A∩B) is at most P(A) and P(B)
    and at least P(A) + P(B) - 1; P(A∪B) is at least P(A) and P(B) and at most P(A) + P(B);
    mutually exclusive events have P(A∩B) = 0.
    """
    problems = []
    for key, v in values.items():
        if not 0 <= v <= 1:
            problems.append("%s = %s is not a probability: it must be between 0 and 1." % (key, v))
    if problems:
        return problems
    eps = 1e-9
    a, b = values.get("P(A)"), values.get("P(B)")
    ab, union = values.get("P(A∩B)"), values.get("P(A∪B)")
    if ab is not None:
        for key in ("P(A)", "P(B)"):
            if key in values and ab > values[key] + eps:
                problems.append("P(A∩B) cannot be larger than %s." % key)
        if a is not None and b is not None and ab < a + b - 1 - eps:
            problems.append("P(A∩B) must be at least P(A) + P(B) - 1 = %s." % round(a + b - 1, 6))
        if exclusive and ab > eps:
            problems.append("Mutually exclusive events have P(A∩B) = 0.")
    if union is not None:
        for key in ("P(A)", "P(B)"):
            if key in values and union < values[key] - eps:
                problems.append("P(A∪B) cannot be smaller than %s." % key)
        if a is not None and b is not None and union > a + b + eps:
            problems.append("P(A∪B) cannot be larger than P(A) + P(B).")
    return problems


def parse(question):
    q = question or ""
    rest = q
    values = {}
    for key, pattern in (("P(A∩B)", JOINT), ("P(A|B)", COND), ("P(A∪B)", UNION),
                         ("P(A)", SINGLE["P(A)"]), ("P(B)", SINGLE["P(B)"])):
        v, rest = _grab(pattern, rest)
        if v is not None and v == v:
            values[key] = round(v, 6)

    low = q.lower()
    exclusive = bool(re.search(r"mutually exclusive|disjoint|\bexclusive\b", low))
    independent = "independen" in low
    conditional = bool(re.search(COND, q, flags=re.I)) or bool(re.search(r"\bgiven\b|conditional", low))
    union = bool(re.search(UNION, q, flags=re.I)) or bool(re.search(r"addition rule|\bunion\b|\beither\b", low))

    if exclusive and independent:
        qtype = "exclusive_and_independent"
    elif independent:
        qtype = "independence"
    elif conditional:
        qtype = "conditional"
    elif union:
        qtype = "union"
    elif exclusive:
        qtype = "exclusive"
    else:
        qtype = "other"

    specific = bool(re.search(r"\bP\s*\(\s*[AB]", q)) or bool(re.search(r"\bA and B\b", q))
    generic = bool(re.search(r"\bevents?\b", q, flags=re.I))
    pronoun = bool(re.search(PRONOUN, low))
    referent_clear = specific or generic or not pronoun

    problems = check_values(values, exclusive)

    return {"question_type": qtype,
            "question_label": TYPES[qtype],
            "events": "A and B" if specific else ("any two events" if referent_clear
                                                  else "unclear (\"%s\")" % re.search(PRONOUN, low).group(1)),
            "referent_clear": referent_clear,
            "mutually_exclusive": exclusive,
            "values": values,
            "problems": problems}


def from_fields(fields):
    """Build an interpretation from the correction form: the student's edit replaces the inference."""
    qtype = fields.get("question_type") if fields.get("question_type") in TYPES else "other"
    values = {}
    problems = []
    for key in ("P(A)", "P(B)", "P(A∩B)", "P(A|B)", "P(A∪B)"):
        raw = str(fields.get("values", {}).get(key, "")).strip()
        if raw:
            try:
                v = _value(raw)
            except ValueError:
                v = float("nan")
            if v == v:
                values[key] = round(v, 6)
            else:
                problems.append("%s must be a number such as 0.2." % key)
    interp = {"question_type": qtype, "question_label": TYPES[qtype], "events": "A and B",
              "referent_clear": True, "mutually_exclusive": qtype in ("exclusive_and_independent", "exclusive")
              or bool(fields.get("mutually_exclusive")), "values": values, "problems": problems, "corrected": True}
    interp["problems"] += check_values(values, interp["mutually_exclusive"])
    return interp


if __name__ == "__main__":
    print(json.dumps(parse(" ".join(sys.argv[1:]) or "Are they independent? I don't have the numbers."),
                     ensure_ascii=False, indent=1))
