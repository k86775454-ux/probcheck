"""Deterministic checks: arithmetic and conditions are computed in code, never by the model.

    python checker.py "P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?"

check(interp) returns a status, the calculation steps, and a list of facts. Each fact names the
rule it depends on; find_support() then looks that rule up in the notes. A fact whose rule cannot
be found in a current passage is not allowed into the answer.
"""
import json
import math
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
    "indep_conditional": ("independent P(B) > 0 then P(A|B) = P(A) knowing B happened does not change", "2.4"),
}


def fmt(x):
    """How a number is shown: four decimals, or three significant figures for tiny values."""
    if x != x:
        return "undefined"
    if 0 < abs(x) < 1e-4:
        return "%.3g" % x
    return ("%.4f" % x).rstrip("0").rstrip(".")


def eq(x):
    """'=' when the shown number is exact, '≈' when fmt() rounded it (for example 0.1 / 0.3)."""
    return "=" if math.isclose(float(fmt(x)), x, rel_tol=1e-9, abs_tol=0.0) else "≈"


def apart(x, y):
    """x and y written with enough decimals to tell them apart, so a page never says '0.1667 ≠ 0.1667'."""
    if same(x, y) or fmt(x) != fmt(y):
        return fmt(x), fmt(y)
    for places in range(5, 16):
        sx, sy = (("%.*f" % (places, z)).rstrip("0").rstrip(".") for z in (x, y))
        if sx != sy:
            return sx, sy
    return repr(x), repr(y)


def sign(x, shown):
    """'=' or '≈' for a value x written as the string shown."""
    return "=" if math.isclose(float(shown), x, rel_tol=1e-9, abs_tol=0.0) else "≈"


def clean(x, *terms):
    """Drop floating-point noise from a sum or difference of the terms: 0.2 + 0.1 - 0.3 is 5.6e-17, not a
    probability. The noise is relative to the terms, so a real but tiny value (10^-14) is kept."""
    return 0.0 if abs(x) <= 8 * 2.2e-16 * max(abs(t) for t in terms) else x


def same(x, y):
    """Equal up to floating-point noise. There is no absolute allowance, so 10^-16 is not equal to 0."""
    return math.isclose(x, y, rel_tol=1e-9, abs_tol=0.0)


def fit(x, a, b):
    """A P(A∩B) worked out from a rounded P(A∪B) or P(A|B) can land just outside the range it must lie in
    (for example -0.0001). Return the nearest possible value, so no answer is negative or above 1."""
    low = max(0.0, a + b - 1) if None not in (a, b) else 0.0
    high = min(v for v in (a, b, 1.0) if v is not None)
    return min(max(x, low), high)


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


def intersection(interp, skip=()):
    """P(A∩B) when it is given or follows from what the student stated, with the fact and step that
    show how (None when it was simply given). skip names the routes that would be circular for the
    question being asked, for example the union route when the question is P(A∪B)."""
    v = interp["values"]
    a, b, ab = v.get("P(A)"), v.get("P(B)"), v.get("P(A∩B)")
    u, c = v.get("P(A∪B)"), v.get("P(A|B)")

    def how(numbers, step, rule, fact):
        return {"numbers": numbers, "step": step, "fact": _fact(rule, fact)}

    if ab is not None:
        return ab, None
    if "exclusive" not in skip and interp.get("mutually_exclusive"):
        return 0.0, how([0.0], "Mutually exclusive: P(A∩B) = 0", "def_exclusive",
                        "Mutually exclusive events cannot both occur, so P(A∩B) = 0.")
    if "independent" not in skip and interp.get("independent") and None not in (a, b):
        val = a * b
        calc = "P(A)P(B) = %s × %s %s %s" % (fmt(a), fmt(b), eq(val), fmt(val))
        return val, how([a, b, val], "Independent: P(A∩B) = " + calc, "def_independent",
                        "For independent events, P(A∩B) = %s." % calc)
    if "union" not in skip and None not in (a, b, u):
        raw = clean(a + b - u, a, b, u)
        val = fit(raw, a, b)
        calc = "P(A) + P(B) − P(A∪B) = %s + %s − %s %s %s" % (fmt(a), fmt(b), fmt(u), eq(raw), fmt(raw))
        return val, how([a, b, u, raw, val], "P(A∩B) = " + calc + rounded(raw, val), "addition_general",
                        "Rearranging the addition rule, P(A∩B) = %s." % (calc if raw == val else
                        "P(A) + P(B) − P(A∪B) ≈ %s, allowing for rounding" % fmt(val)))
    if "conditional" not in skip and None not in (b, c):
        raw = c * b
        val = fit(raw, a, b)
        calc = "P(A|B)P(B) = %s × %s %s %s" % (fmt(c), fmt(b), eq(raw), fmt(raw))
        return val, how([b, c, raw, val], "P(A∩B) = " + calc + rounded(raw, val), "conditional_def",
                        "Since P(A|B) = P(A∩B) / P(B), P(A∩B) = %s." % (calc if raw == val else
                        "P(A|B)P(B) ≈ %s, allowing for rounding" % fmt(val)))
    # When P(A) or P(B) is 0 or 1, the bounds leave only one possible value.
    if None not in (a, b) and min(a, b) == 0:
        return 0.0, how([a, b, 0.0], "P(A∩B) ≤ min(P(A), P(B)) = 0, so P(A∩B) = 0", "bounds",
                        "P(A∩B) can never be larger than the smaller of P(A) and P(B), which is 0 here, "
                        "so P(A∩B) = 0.")
    if None not in (a, b) and max(a, b) == 1:
        val = min(a, b)
        return val, how([a, b, val, 1.0], "P(A∩B) ≥ P(A) + P(B) − 1 = %s and ≤ min(P(A), P(B)) = %s, so P(A∩B) = %s"
                        % (fmt(val), fmt(val), fmt(val)), "addition_general",
                        "By the addition rule, P(A∪B) = P(A) + P(B) − P(A∩B) ≤ 1, so P(A∩B) ≥ P(A) + P(B) − 1 = %s; "
                        "it is also at most the smaller of P(A) and P(B), so P(A∩B) = %s." % (fmt(val), fmt(val)))
    return None, None


def rounded(raw, val):
    """The note shown when fit() moved a value: rounding, not the probability, put it out of range."""
    if raw == val:
        return ""
    return ("; with rounded values this is just outside the possible range, so the nearest possible value, "
            "%s, is used" % fmt(val))


def show_derivation(out, how):
    """Show how P(A∩B) was obtained: its fact, its calculation step and the numbers it uses."""
    out["facts"].append(how["fact"])
    out["steps"].append(how["step"])
    out["numbers"] += how["numbers"]


def as_given(out, key, x):
    """The value asked for was typed in, and the other values agree with it: show it back."""
    out["numbers"] += [x]
    out["steps"].append("%s %s %s, as you gave it" % (key, eq(x), fmt(x)))
    out["verdict"] = fmt(x)
    return out


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
                        "Independent would need: P(A)P(B) = %s × %s %s %s" % (fmt(a), fmt(b), eq(prod), fmt(prod)),
                        "0 %s %s" % ("=" if prod == 0 else "≠", fmt(prod))]
        if a > 0 and b > 0:      # decide on the inputs, not on whether a tiny product looks like zero
            out["facts"].append(_fact("excl_pos_not_indep",
                "With P(A) = %s and P(B) = %s, both events have positive probability, so P(A)P(B) %s %s "
                "while P(A∩B) = 0: they cannot be both mutually exclusive and independent."
                % (fmt(a), fmt(b), eq(prod), fmt(prod))))
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
        ab, how = intersection(interp, skip=("independent",))
        if how:
            show_derivation(out, how)
        missing = [k for k, x in (("P(A)", a), ("P(B)", b), ("P(A∩B)", ab)) if x is None]
        if missing:
            # No numbers at all and no specific events: the definition itself is the answer.
            out["status"] = "checked" if len(missing) == 3 and interp["events"] == "any two events" else "depends"
            out["needs"] = missing if out["status"] == "depends" else []
            return out
        prod = a * b
        indep = same(prod, ab)
        ab_s, prod_s = apart(ab, prod)            # more decimals only if the usual four would look equal
        out["numbers"] += [a, b, ab, prod, float(ab_s), float(prod_s)]
        out["steps"] += ["P(A)P(B) = %s × %s %s %s" % (fmt(a), fmt(b), sign(prod, prod_s), prod_s),
                         "P(A∩B) %s %s" % (sign(ab, ab_s), ab_s),
                         "%s %s %s" % (ab_s, "=" if indep else "≠", prod_s)]
        if not indep and fmt(ab) == fmt(prod):
            out["steps"].append("These differ only after rounding. If you meant them to be equal, enter "
                                "exact fractions such as 1/6.")
        out["facts"].append(_fact("def_independent",
            "Here P(A)P(B) %s %s and P(A∩B) %s %s, so A and B are %s."
            % (sign(prod, prod_s), prod_s, sign(ab, ab_s), ab_s, "independent" if indep else "not independent")))
        out["verdict"] = "independent" if indep else "not independent"
        return out

    if t == "conditional":
        out["topic"] = "Conditional probability"
        out["facts"].append(_fact("conditional_def", "P(A|B) = P(A∩B) / P(B), defined only when P(B) > 0."))
        ab, how = intersection(interp, skip=("conditional",))
        if how:
            show_derivation(out, how)
        if b == 0:
            out["steps"].append("P(B) = 0, so P(A∩B) / P(B) is undefined")
            out["facts"].append(_fact("conditional_def", "Because P(B) = 0, P(A|B) is not defined."))
            out["verdict"] = "undefined"
            return out
        missing = [k for k, x in (("P(A∩B)", ab), ("P(B)", b)) if x is None]
        if missing and v.get("P(A|B)") is not None:
            return as_given(out, "P(A|B)", v["P(A|B)"])
        if b is None and interp.get("independent") and a is not None:
            out["numbers"] += [a]
            out["steps"].append("Independent: P(A|B) = P(A) %s %s, provided P(B) > 0" % (eq(a), fmt(a)))
            out["facts"].append(_fact("indep_conditional", "If A and B are independent and P(B) > 0, then "
                                      "P(A|B) = P(A) = %s: knowing that B happened does not change the "
                                      "probability of A." % fmt(a)))
            out["verdict"] = fmt(a)
            return out
        if b is None and ab == 0:
            out["numbers"] += [0.0]
            out["steps"].append("P(A|B) = 0 / P(B) = 0, provided P(B) > 0")
            out["facts"].append(_fact("conditional_def", "With P(A∩B) = 0, P(A|B) = P(A∩B) / P(B) = 0 "
                                      "whenever P(B) > 0."))
            out["verdict"] = "0"
            return out
        if missing:
            # With no numbers at all, the definition is the answer; with some, say what else is needed.
            out["status"] = "checked" if not v else "depends"
            out["needs"] = missing if out["status"] == "depends" else []
            return out
        val = ab / b
        out["numbers"] += [ab, b, val]
        out["steps"].append("P(A|B) = P(A∩B) / P(B) = %s / %s %s %s" % (fmt(ab), fmt(b), eq(val), fmt(val)))
        out["facts"].append(_fact("conditional_def", "So the conditional probability is P(A|B) = P(A∩B) / P(B) = %s / %s %s %s."
                                  % (fmt(ab), fmt(b), eq(val), fmt(val))))
        out["verdict"] = fmt(val)
        return out

    if t == "union":
        out["topic"] = "Addition rule"
        exclusive = interp.get("mutually_exclusive") and v.get("P(A∩B)") is None
        if exclusive:
            out["facts"].append(_fact("addition_exclusive", "For mutually exclusive events, P(A∪B) = P(A) + P(B)."))
            ab, how = 0.0, None
        else:
            out["facts"].append(_fact("addition_general", "The general addition rule is P(A∪B) = P(A) + P(B) − P(A∩B)."))
            ab, how = intersection(interp, skip=("union",))
            if how:
                show_derivation(out, how)
        missing = [k for k, x in (("P(A)", a), ("P(B)", b), ("P(A∩B)", ab)) if x is None]
        if missing and v.get("P(A∪B)") is not None:
            return as_given(out, "P(A∪B)", v["P(A∪B)"])
        if missing:
            # With no numbers and no stated premise, the rule is the answer; otherwise say what is needed.
            out["status"] = "checked" if not v and len(missing) == 3 else "depends"
            out["needs"] = missing if out["status"] == "depends" else []
            return out
        val = a + b - ab
        out["numbers"] += [a, b, ab, val]
        out["steps"].append("P(A∪B) = P(A) + P(B) − P(A∩B) = %s + %s − %s %s %s" % (fmt(a), fmt(b), fmt(ab), eq(val), fmt(val)))
        if exclusive:
            out["facts"].append(_fact("addition_exclusive", "So for these mutually exclusive events, "
                                      "P(A∪B) = P(A) + P(B) = %s + %s %s %s." % (fmt(a), fmt(b), eq(val), fmt(val))))
        else:
            out["facts"].append(_fact("addition_general", "So by the addition rule, P(A∪B) = P(A) + P(B) − "
                                      "P(A∩B) = %s + %s − %s %s %s." % (fmt(a), fmt(b), fmt(ab), eq(val), fmt(val))))
        out["verdict"] = fmt(val)
        return out

    if t == "intersection":
        out["topic"] = "Probability rules"
        if v.get("P(A∩B)") is not None:
            out["facts"].append(_fact("bounds", "Every probability lies between 0 and 1, and P(A∩B) can never be "
                                                "larger than the smaller of P(A) and P(B)."))
            return as_given(out, "P(A∩B)", v["P(A∩B)"])
        ab, how = intersection(interp)
        if how is None:
            out["status"] = "depends"
            out["needs"] = ["P(A∪B) with P(A) and P(B), or P(A|B) with P(B)"]
            out["facts"].append(_fact("addition_general", "The general addition rule is P(A∪B) = P(A) + P(B) − P(A∩B)."))
            return out
        show_derivation(out, how)
        out["verdict"] = fmt(ab)
        return out

    if t == "exclusive":
        out["topic"] = "Mutually exclusive events"
        out["facts"].append(_fact("def_exclusive", "Two events are mutually exclusive if they cannot both "
                                                   "occur, so P(A∩B) = 0."))
        ab, how = intersection(interp, skip=("exclusive",))   # here exclusivity is the question, not a given
        if ab is None:
            if a is not None and b is not None and a + b > 1 + 1e-12:
                low = a + b - 1
                out["numbers"] = [a, b, a + b, low]
                out["steps"].append("P(A∪B) ≤ 1, so P(A∩B) ≥ P(A) + P(B) − 1 = %s + %s − 1 %s %s > 0"
                                    % (fmt(a), fmt(b), eq(low), fmt(low)))
                out["facts"].append(_fact("addition_general",
                    "By the addition rule P(A∪B) = P(A) + P(B) − P(A∩B) ≤ 1, so P(A∩B) ≥ %s + %s − 1 %s %s, "
                    "which is above 0: A and B are not mutually exclusive." % (fmt(a), fmt(b), eq(low), fmt(low))))
                out["verdict"] = "not mutually exclusive"
            elif a is not None or b is not None:
                out["status"] = "depends"
                out["needs"] = ["P(A∩B)"]
            return out
        if how:
            show_derivation(out, how)
        verdict = "mutually exclusive" if ab == 0 else "not mutually exclusive"   # sums went through clean()
        out["numbers"] += [ab, 0]
        out["steps"].append("P(A∩B) %s %s, so A and B are %s" % (eq(ab), fmt(ab), verdict))
        out["facts"].append(_fact("def_exclusive", "Here P(A∩B) %s %s, so A and B are %s." % (eq(ab), fmt(ab), verdict)))
        out["verdict"] = verdict
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
