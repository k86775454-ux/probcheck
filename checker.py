"""Deterministic checks: arithmetic and conditions are computed in code, never by the model.

    python checker.py "P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?"

check(interp) returns a status, the calculation steps, and a list of facts. Each fact names the
rule it depends on; find_support() then looks that rule up in the notes. A fact whose rule cannot
be found in a current passage is not allowed into the answer.
"""
import json
import sys

import retrieve

THRESHOLD = 0.25  # relative lexical score from Lab 4; a ranking signal, not a probability
EPS = 1e-9

# Each rule is looked up in the notes with a focused query. The query text is ours; the
# supporting sentence comes from the corpus.
RULES = {
    # rule: (query, section the rule belongs to)
    "def_exclusive": ("mutually exclusive cannot both occur P(A∩B) = 0", "2.1"),
    "def_independent": ("events independent if P(A∩B) = P(A)P(B)", "2.3"),
    "excl_pos_not_indep": ("mutually exclusive both positive probability cannot be independent", "2.3"),
    "excl_zero_indep": ("either event probability zero mutually exclusive also independent", "2.3"),
    "addition_general": ("general addition rule P(A∪B) = P(A) + P(B) − P(A∩B)", "2.2"),
    "addition_exclusive": ("mutually exclusive addition rule simplifies P(A∪B) = P(A) + P(B)", "2.1"),
    "conditional_def": ("conditional probability A given B P(A|B) = P(A∩B) / P(B) defined only when P(B) > 0", "2.4"),
    "bounds": ("every probability between 0 and 1 P(A∩B) never larger than smaller", "2.2"),
}


def fmt(x):
    return ("%.4f" % x).rstrip("0").rstrip(".") if x == x else "undefined"


def find_support(rule):
    """Best current passage for a rule, or None if nothing in the notes scores above THRESHOLD.

    The search is limited to the rule's own section. An earlier version searched the whole corpus
    and matched the independence definition to a sentence in 2.4 that merely mentions independence."""
    query, section = RULES[rule]
    hits = [h for h in retrieve.retrieve(query, k=50)
            if not h["superseded"] and h["section"].startswith(section + " ")]
    return hits[0] if hits and hits[0]["score"] >= THRESHOLD else None


def _fact(rule, text):
    return {"rule": rule, "text": text}


def check(interp):
    t = interp["question_type"]
    v = interp["values"]
    a, b, ab = v.get("P(A)"), v.get("P(B)"), v.get("P(A∩B)")
    out = {"status": "checked", "facts": [], "steps": [], "needs": [], "numbers": [], "topic": None}

    if interp.get("problems"):
        out.update(status="invalid", needs=list(interp["problems"]))
        out["facts"].append(_fact("bounds", "Every probability lies between 0 and 1, and P(A∩B) "
                                            "can never be larger than the smaller of P(A) and P(B)."))
        out["topic"] = "Probability rules"
        return out

    if t == "exclusive_and_independent":
        out["topic"] = "Independence and mutually exclusive events"
        out["facts"].append(_fact("def_exclusive", "Mutually exclusive events cannot both occur, so P(A∩B) = 0."))
        out["facts"].append(_fact("def_independent", "Independence means P(A∩B) = P(A)P(B)."))
        if a is None or b is None:
            out["status"] = "depends"
            out["needs"] = [k for k, x in (("P(A)", a), ("P(B)", b)) if x is None]
            out["facts"].append(_fact("excl_pos_not_indep", "If both events have positive probability, "
                                      "they cannot be both mutually exclusive and independent."))
            out["facts"].append(_fact("excl_zero_indep", "If either event has probability zero, "
                                      "mutually exclusive events are also independent."))
            return out
        prod = a * b
        out["numbers"] = [a, b, prod, 0]
        out["steps"] = ["Mutually exclusive: P(A∩B) = 0",
                        "Independent would need: P(A)P(B) = %s × %s = %s" % (fmt(a), fmt(b), fmt(prod)),
                        "0 %s %s" % ("=" if abs(prod) < EPS else "≠", fmt(prod))]
        if prod > EPS:
            out["facts"].append(_fact("excl_pos_not_indep",
                "With P(A) = %s and P(B) = %s, both events have positive probability, so P(A)P(B) = %s "
                "while P(A∩B) = 0: they cannot be both mutually exclusive and independent."
                % (fmt(a), fmt(b), fmt(prod))))
            out["verdict"] = "not independent"
        else:
            out["facts"].append(_fact("excl_zero_indep",
                "Because one event has probability zero, P(A)P(B) = 0 = P(A∩B), so these mutually "
                "exclusive events are also independent."))
            out["verdict"] = "independent"
        return out

    if t == "independence":
        out["topic"] = "Independence"
        out["facts"].append(_fact("def_independent", "Events A and B are independent if P(A∩B) = P(A)P(B)."))
        if interp.get("mutually_exclusive") and ab is None:
            ab = 0.0
        missing = [k for k, x in (("P(A)", a), ("P(B)", b), ("P(A∩B)", ab)) if x is None]
        if missing:
            # No numbers at all and no specific events: the definition itself is the answer.
            out["status"] = "checked" if len(missing) == 3 and interp["events"] == "any two events" else "depends"
            out["needs"] = missing if out["status"] == "depends" else []
            return out
        prod = a * b
        same = abs(prod - ab) < EPS
        out["numbers"] = [a, b, ab, prod]
        out["steps"] = ["P(A)P(B) = %s × %s = %s" % (fmt(a), fmt(b), fmt(prod)),
                        "P(A∩B) = %s" % fmt(ab),
                        "%s %s %s" % (fmt(ab), "=" if same else "≠", fmt(prod))]
        out["facts"].append(_fact("def_independent",
            "Here P(A)P(B) = %s and P(A∩B) = %s, so A and B are %s."
            % (fmt(prod), fmt(ab), "independent" if same else "not independent")))
        out["verdict"] = "independent" if same else "not independent"
        return out

    if t == "conditional":
        out["topic"] = "Conditional probability"
        out["facts"].append(_fact("conditional_def", "P(A|B) = P(A∩B) / P(B), defined only when P(B) > 0."))
        missing = [k for k, x in (("P(A∩B)", ab), ("P(B)", b)) if x is None]
        if missing:
            out["status"] = "depends" if len(missing) < 2 else "checked"
            out["needs"] = missing if out["status"] == "depends" else []
            return out
        if b < EPS:
            out["steps"] = ["P(B) = 0, so P(A∩B) / P(B) is undefined"]
            out["facts"].append(_fact("conditional_def", "Because P(B) = 0, P(A|B) is not defined."))
            out["verdict"] = "undefined"
            return out
        val = ab / b
        out["numbers"] = [ab, b, val]
        out["steps"] = ["P(A|B) = P(A∩B) / P(B) = %s / %s = %s" % (fmt(ab), fmt(b), fmt(val))]
        out["facts"].append(_fact("conditional_def", "So P(A|B) = %s / %s = %s." % (fmt(ab), fmt(b), fmt(val))))
        out["verdict"] = fmt(val)
        return out

    if t == "union":
        out["topic"] = "Addition rule"
        if interp.get("mutually_exclusive") and ab is None:
            out["facts"].append(_fact("addition_exclusive", "For mutually exclusive events, P(A∪B) = P(A) + P(B)."))
            ab = 0.0
        else:
            out["facts"].append(_fact("addition_general", "The general addition rule is P(A∪B) = P(A) + P(B) − P(A∩B)."))
        missing = [k for k, x in (("P(A)", a), ("P(B)", b), ("P(A∩B)", ab)) if x is None]
        if missing:
            out["status"] = "depends" if len(missing) < 3 else "checked"
            out["needs"] = missing if out["status"] == "depends" else []
            return out
        val = a + b - ab
        out["numbers"] = [a, b, ab, val]
        out["steps"] = ["P(A∪B) = %s + %s − %s = %s" % (fmt(a), fmt(b), fmt(ab), fmt(val))]
        rule = "addition_exclusive" if interp.get("mutually_exclusive") else "addition_general"
        out["facts"].append(_fact(rule, "So P(A∪B) = %s + %s − %s = %s." % (fmt(a), fmt(b), fmt(ab), fmt(val))))
        out["verdict"] = fmt(val)
        return out

    if t == "exclusive":
        out["topic"] = "Mutually exclusive events"
        out["facts"].append(_fact("def_exclusive", "Two events are mutually exclusive if they cannot both "
                                                   "occur, so P(A∩B) = 0."))
        return out

    out.update(status="cannot_check", topic=None)
    return out


if __name__ == "__main__":
    import parse
    q = " ".join(sys.argv[1:]) or "P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?"
    result = check(parse.parse(q))
    for f in result["facts"]:
        s = find_support(f["rule"])
        f["support"] = s["id"] if s else None
    print(json.dumps(result, ensure_ascii=False, indent=1))
