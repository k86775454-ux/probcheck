"""Turn a student's question into an interpretation the student can see and correct.

    python parse.py "Are they independent? I don't have the numbers."

The interpretation is an inference about what the student meant, so it is always shown on the page
and can be edited (Correct these details). Nothing here decides the answer: it only reads the
question type, which events are meant and which probabilities were given, and lists problems.
"""
import decimal
import itertools
import json
import math
import re
import sys

# A number: 30% or 30 percent, 3/10, 0.3, .3, 3 or 1e-3. A minus sign is read, then rejected. The number
# must end there: "0,3" (a decimal comma), "0.5/2" or "0.3and" is not read in part, but reported (parse).
END = r"(?=$|\s|[;!?)\]]|,(?!\d)|\.(?!\d))"
NUM = (r"(-?\s*\d+(?:\.\d+)?\s*(?:%|percent\b)|-?\s*\d+\s*/\s*\d+"
       r"|-?\s*(?:\d+(?:\.\d*)?|\.\d+)(?:e-?\d+)?)" + END)
SAYS = r"(?:=|\bis\b|:|\bequals?\b|≈)"     # "P(A) = 0.3", "P(A) is 0.3", "P(A): 0.3", "P(A) equals 0.3"
PR = r"Pr?\s*\(\s*"                              # P( or Pr(
AND = r"(?:∩|⋂|intersection|intersect|and|cap|n|&|∧|,)"
OR = r"(?:∪|⋃|union|cup|or|u|∨)"
JOINT = PR + r"A\s*" + AND + r"\s*B\s*\)|" + PR + r"AB\s*\)"
COND = PR + r"A\s*\|\s*B\s*\)"
UNION = PR + r"A\s*" + OR + r"\s*B\s*\)"
SINGLE = {"P(A)": PR + r"A\s*\)", "P(B)": PR + r"B\s*\)"}
# Complements and P(B|A) are outside the notes: P(A'), P(A^c), P(not A), P(B|A), P(A|B')
UNSUPPORTED = PR + r"[^)]*?(?:'|’|\^\s*c\b|ᶜ|\u0304|Ā|B̄|\bnot\b|~|¬|B\s*\|\s*A\b)[^)]*\)"
PRONOUN = r"\b(they|them|these|those|it|this one|both)\b"
# "not mutually exclusive", "aren't disjoint": a negation must not switch the assumption on
NOT_EXCLUSIVE = r"(?:\bnot\b|n't\b|\bnever\b)\s+(?:\w+\s+){0,2}?(?:mutually\s+exclusive|disjoint|exclusive)"
NOT_INDEPENDENT = r"(?:\bnot\b|n't\b|\bnever\b)\s+(?:\w+\s+){0,2}?independent"
# "dependent" means "not independent", and "not dependent" means "independent"
NOT_DEPENDENT = r"(?:\bnot\b|n't\b|\bnever\b)\s+(?:\w+\s+){0,2}?\bdependent\b"
# The quantity asked for: "What is P(A∪B)?", "find P(A|B)", or "P(A or B)?" with no value after it.
TARGET = (r"(?:what\s+is|what's|find|compute|calculate|work\s+out)\s+(?:the\s+(?:probability|value)\s+(?:of\s+)?)?"
          r"(Pr?\s*\([^)=]*\))|(Pr?\s*\([^)=]*\))\s*=?\s*\?")
# A property asked about rather than stated: "Are A and B mutually exclusive?", "Are they independent?"
SUBJECT = r"(?:a\s+and\s+b|a,\s*b|they|these(?:\s+two)?\s+events|the\s+(?:two\s+)?events)"
BARE = r"(?:^|[.!?;,]\s*)"                      # a bare question such as "... P(A∩B)=0.12. Independent?"
# The question word order ("Are A and B ...") marks a question, with or without a question mark.
ASKED_EXCLUSIVE = (r"\b(?:are|is|can|could)\s+" + SUBJECT + r"\s+(?:\w+\s+)?(?:mutually\s+exclusive|disjoint)"
                   + "|" + BARE + r"(?:mutually\s+exclusive|disjoint)\s*\?")
ASKED_INDEPENDENT = (r"\b(?:are|is|can|could)\s+" + SUBJECT + r"\s+(?:\w+\s+)?(?:in)?dependent"
                     r"|\bis\s+a\s+(?:\w+\s+)?(?:in)?dependent\s+(?:of|from|on)\s+b\b"
                     + "|" + BARE + r"(?:in)?dependent\s*\?")
# The quantity asked for in words: "the probability of A or B", "... that both A and B occur", "... of A given B"
WORD_TARGET = (("union", r"probability\s+(?:of|that)\s+(?:either\s+)?a\s+or\s+b\b"),
               ("intersection", r"probability\s+(?:of|that)\s+(?:both\s+)?a\s+and\s+b\b"),
               ("conditional", r"probability\s+(?:of|that)\s+a\s+(?:\w+\s+)?given\s+(?:that\s+)?b\b"))
# Words inside P(...) that are operators, not events: P(A and B), P(A n B), P(A u B), P(A^c)
OPERATORS = {"and", "or", "not", "given", "intersect", "intersection", "union", "cap", "cup", "n", "u", "c"}
# Phrases in which a capital letter can only name an event, so "I" and "P" count there too:
# "Are I and B independent?", "I and B are ...", "independent of P", "event P", "the probability of I or B"
EVENT_PHRASES = (
    r"\b(?i:are|is|were|was|can|could|be|whether|if|that|both|either|events?)\s+"
    r"([A-Z])\s*(?:and|or|&|,)\s*([A-Z])\b",
    r"\b([A-Z])\s*(?:and|or|&|,)\s*([A-Z])\s+(?:are|were|be|is|can|could|independent|dependent|mutually|"
    r"disjoint|exclusive)\b",
    r"\b(?:independent|dependent|exclusive|disjoint)\s+(?:of|from|with)\s+([A-Z])\b",
    r"\b([A-Z])\s+(?:is\s+|are\s+)?(?:in)?dependent\s+(?:of|from)\b",
    r"\b(?i:events?)\s+([A-Z])\b",
    r"\b(?i:probability\s+(?:of|that)\s+(?:both\s+|either\s+)?)([A-Z])\s+(?:and|or|given)\s+(?:that\s+)?([A-Z])\b",
)

TYPES = {
    "exclusive_and_independent": "Can mutually exclusive events also be independent?",
    "independence": "Are A and B independent?",
    "conditional": "What is P(A|B)?",
    "union": "What is P(A∪B)?",
    "intersection": "What is P(A∩B)?",
    "exclusive": "Are A and B mutually exclusive?",
    "other": "Something the notes may not cover",
}


def _value(text):
    text = text.replace(" ", "").lower().replace("percent", "%")
    if text.endswith("%"):                    # 25.74% is 0.2574 exactly, not 25.74 / 100 = 0.25739999999999996
        return float(decimal.Decimal(text[:-1]) / 100)
    if "/" in text:
        a, b = text.split("/")
        return float(a) / float(b) if float(b) else float("nan")
    return float(text)


def _named_events(q):
    """Every event letter the question names, so that "Are C and D independent?" is never answered
    about A and B. Letters are read in P(...) in any case. In words, any single capital letter counts
    except "I" (a pronoun) and "P" (as in "find P"), and those two count too in a phrase where only an
    event fits (EVENT_PHRASES). Lower-case pairs such as "c and d" count as well."""
    names = set()
    for inside in re.findall(r"\bPr?\s*\(([^()]*)\)", q, flags=re.I):
        for token in re.findall(r"[A-Za-z]+", inside):
            if token.lower() in OPERATORS:
                continue
            if len(token) == 1 or (token.isupper() and len(token) <= 3):        # P(A), P(AB)
                names.update(token.upper())
    words = re.sub(r"\bPr?\s*\([^()]*\)", " ", q, flags=re.I)
    names.update(re.findall(r"\b([A-HJ-OQ-Z])\b(?!\s*[:)])", words))     # not "Q:" or "c)"
    for pattern in EVENT_PHRASES:
        for found in re.findall(pattern, words):
            names.update(found if isinstance(found, tuple) else (found,))
    for x, y in re.findall(r"\b([a-z])\s+(?:and|or|given|,)\s+([a-z])\b", words) + re.findall(
            r"\b([a-z])\s+(?:is\s+)?(?:in)?dependent\s+(?:of|from)\s+([a-z])\b", words):
        names.update({x.upper(), y.upper()})
    return names


def slack(x):
    """How far a typed P(A∪B) or P(A|B) may be from the true value because it was rounded: half a unit
    in its last digit (0.6667 may stand for 2/3, 0.0032 for 0.00316), and never more than TOL. A value
    with many digits, or a fraction such as 2/3, therefore gets almost no allowance, and a small value
    such as 3e-7 only 5e-8, so rounding never hides an impossible combination of small probabilities."""
    if x is None:
        return 0.0
    digits, _, exponent = repr(float(x)).partition("e")
    places = len(digits.partition(".")[2])
    return min(TOL, 0.5 * 10 ** (int(exponent or 0) - places)) + 1e-12     # + floating-point noise


SMALLEST = 1e-9   # positive probabilities below this are too small to check reliably


def _grab(pattern, text):
    """Return (value, text with the match removed) for 'pattern = number'."""
    m = re.search("(%s)\\s*%s\\s*%s" % (pattern, SAYS, NUM), text, flags=re.I)
    if not m:
        return None, text
    return _value(m.group(2)), text[:m.start()] + " " + text[m.end():]


def _n(x):
    return ("%.6f" % x).rstrip("0").rstrip(".")


TOL = 5e-4   # a value the student gives for P(A∪B) or P(A|B) may be rounded to three decimals


def check_values(values, exclusive=False, independent=False, not_exclusive=False, not_independent=False):
    """Problems with the numbers themselves, shared by the question parser and the correction form.

    Each value must lie in [0, 1], and the values must fit together: P(A∩B) is at most P(A) and P(B)
    and at least P(A) + P(B) - 1; mutually exclusive events have P(A∩B) = 0, which applies even when
    P(A∩B) is not typed (so P(A) + P(B) must be at most 1); independent events have
    P(A∩B) = P(A)P(B); a given P(A∪B) or P(A|B) must match what the other values imply, allowing for
    rounding (slack); P(A|B) needs P(B) > 0; and a stated "not mutually exclusive" or "not independent"
    must not be contradicted. These checks name the problem. A last test (_possible) catches any other
    combination that no pair of events can have.
    """
    problems = []
    for key, v in values.items():
        if not 0 <= v <= 1:
            problems.append("%s = %s is not a probability: it must be between 0 and 1." % (key, v))
        elif 0 < v < SMALLEST:
            problems.append("%s = %s is too small for me to check reliably: use 0, or a value of at least "
                            "0.000000001." % (key, v))
    if problems:
        return problems
    eps = 1e-12                                 # floating-point noise only: typed values are exact
    a, b = values.get("P(A)"), values.get("P(B)")
    ab, union, cond = values.get("P(A∩B)"), values.get("P(A∪B)"), values.get("P(A|B)")
    implied = ab is None and exclusive          # mutually exclusive: P(A∩B) = 0 even if not typed
    if implied:
        ab = 0.0
    if ab is not None:
        for key in ("P(A)", "P(B)"):
            if key in values and ab > values[key] + eps:
                problems.append("P(A∩B) cannot be larger than %s." % key)
        if a is not None and b is not None and ab < a + b - 1 - eps:
            if implied:
                problems.append("Mutually exclusive events need P(A) + P(B) ≤ 1, but here "
                                "P(A) + P(B) = %s." % _n(a + b))
            else:
                problems.append("P(A∩B) must be at least P(A) + P(B) - 1 = %s." % _n(a + b - 1))
        if exclusive and ab > 0:
            problems.append("Mutually exclusive events have P(A∩B) = 0.")
    if union is not None:                       # a typed P(A∪B) or P(A|B) may be rounded: allow slack
        su = slack(union)
        for key in ("P(A)", "P(B)"):
            if key in values and union < values[key] - su:
                problems.append("P(A∪B) cannot be smaller than %s." % key)
        if a is not None and b is not None and union > a + b + su:
            problems.append("P(A∪B) cannot be larger than P(A) + P(B).")
        elif None not in (a, b, ab) and abs(union - (a + b - ab)) > su:
            problems.append("P(A∪B) = %s does not match P(A) + P(B) - P(A∩B) = %s."
                            % (_n(union), _n(a + b - ab)))
        if ab is not None and union < ab - su:
            problems.append("P(A∪B) cannot be smaller than P(A∩B).")
    if cond is not None:
        sc = slack(cond)
        if b == 0 or union == 0:
            problems.append("P(A|B) is not defined when P(B) = 0%s." % (" (P(A∪B) = 0 makes P(B) = 0)" if b != 0 else ""))
        elif cond > sc and (a == 0 or ab == 0):
            # P(A|B) = P(A∩B) / P(B) is 0 whenever P(B) > 0: no rounding allowance can change that
            problems.append("P(A|B) = %s is impossible when %s: P(A|B) = P(A∩B) / P(B) = 0 whenever P(B) > 0."
                            % (_n(cond), "P(A) = 0" if a == 0 else
                               "A and B are mutually exclusive" if implied else "P(A∩B) = 0"))
        elif a == 1 and cond < 1 - sc:
            problems.append("P(A|B) = %s is impossible when P(A) = 1: then P(A∩B) = P(B), so P(A|B) = 1."
                            % _n(cond))
        elif ab is not None and cond < ab - sc:
            problems.append("P(A|B) cannot be smaller than P(A∩B), because P(A|B) = P(A∩B) / P(B) and "
                            "P(B) is at most 1.")
        elif ab is not None and b is not None and abs(cond - ab / b) > sc:
            problems.append("P(A|B) = %s does not match P(A∩B) / P(B) = %s." % (_n(cond), _n(ab / b)))
    if independent and a is not None and b is not None:
        if exclusive and a > 0 and b > 0:
            problems.append("Events with positive probabilities cannot be both mutually exclusive and "
                            "independent.")
        elif ab is not None and not math.isclose(ab, a * b, rel_tol=1e-9):
            problems.append("Independent events need P(A∩B) = P(A)P(B) = %s, but here P(A∩B) = %s."
                            % (_n(a * b), _n(ab)))
    if independent and cond is not None and a is not None and abs(cond - a) > slack(cond):
        problems.append("For independent events P(A|B) = P(A) = %s, but here P(A|B) = %s." % (_n(a), _n(cond)))
    if not problems:
        problems += _intersection_conflicts(values, exclusive, independent)
    if not problems:
        problems += _negations(values, exclusive, not_exclusive, not_independent)
    if not problems and not _possible(values, exclusive, independent):
        problems.append("These values cannot all be true for the same two events, even allowing for "
                        "rounding. One of them may be a typo.")
    return problems


def _routes(values, exclusive, independent):
    """Every way the givens fix P(A∩B): (name, value, how far rounding may have moved it)."""
    a, b = values.get("P(A)"), values.get("P(B)")
    ab, union, cond = values.get("P(A∩B)"), values.get("P(A∪B)"), values.get("P(A|B)")
    routes = []
    if ab is not None:
        routes.append(("the P(A∩B) you gave", ab, 0.0))
    if exclusive:
        routes.append(("mutual exclusivity", 0.0, 0.0))
    if independent and None not in (a, b):
        routes.append(("independence, P(A)P(B),", a * b, 0.0))
    if union is not None and None not in (a, b):
        routes.append(("P(A) + P(B) - P(A∪B)", a + b - union, slack(union)))
    if cond is not None and b is not None:
        routes.append(("P(A|B)P(B)", cond * b, slack(cond) * b))
    if None not in (a, b) and (min(a, b) == 0 or max(a, b) == 1):
        routes.append(("the bounds on P(A∩B)", min(a, b) if max(a, b) == 1 else 0.0, 0.0))
    return routes


def _intersection_conflicts(values, exclusive, independent):
    """P(A∩B) can follow from several givens; they must agree and stay within its bounds.

    For example, independence gives P(A)P(B), P(A∪B) gives P(A) + P(B) - P(A∪B) and P(A|B) gives
    P(A|B)P(B). Any one of them can make an otherwise plausible set of values impossible."""
    a, b = values.get("P(A)"), values.get("P(B)")
    routes = _routes(values, exclusive, independent)
    if not routes:
        return []
    first, x0, e0 = routes[0]
    for name, x, e in routes[1:]:
        if abs(x - x0) > e + e0 + 1e-12:
            return ["These values disagree about P(A∩B): %s gives %s, but %s gives %s."
                    % (first, _n(x0), name, _n(x))]
    low = max(0.0, (a + b - 1) if None not in (a, b) else 0.0)
    high = min(v for v in (a, b, 1.0) if v is not None)
    if not low - e0 - 1e-12 <= x0 <= high + e0 + 1e-12:
        return ["%s gives P(A∩B) = %s, but with these values P(A∩B) must lie between %s and %s."
                % (first[0].upper() + first[1:], _n(x0), _n(low), _n(high))]
    return []


def _negations(values, exclusive, not_exclusive, not_independent):
    """A stated "not mutually exclusive" or "not independent" must not be contradicted by values that fix
    P(A∩B) exactly (a P(A∩B) you gave, mutual exclusivity, or P(A) or P(B) being 0 or 1)."""
    a, b = values.get("P(A)"), values.get("P(B)")
    exact = [x for name, x, e in _routes(values, exclusive, False) if e == 0]
    if not exact:
        return []
    ab = exact[0]
    if not_exclusive and ab == 0:
        return ["You said A and B are not mutually exclusive, but with these values P(A∩B) = 0."]
    if not_independent and None not in (a, b) and math.isclose(ab, a * b, rel_tol=1e-9, abs_tol=0.0):
        return ["You said A and B are not independent (dependent), but with these values "
                "P(A∩B) = P(A)P(B) = %s." % _n(ab)]
    return []


def _possible(values, exclusive, independent):
    """Last test: is there any pair of events with all of these values (allowing for rounding)?

    The checks above give a specific reason for the common mistakes; this one catches the rest, for
    example P(A) = 0.97, P(A∩B) = 0.1 and P(A|B) = 0.61, which force P(B) ≈ 0.16 and then break the
    lower bound on P(A∩B). The unknowns are x = (P(A), P(B), P(A∩B)), with the known ones put in
    exactly. Every rule is a linear inequality in x, so the allowed x form a convex polytope inside the
    unit cube. A non-empty polytope of this kind has a corner, where as many boundary planes meet as
    there are unknowns, so trying every such set of planes decides the question. P(A|B) also needs
    P(B) > 0: then some corner must have P(B) > 0, because P(B) is largest at a corner."""
    a, b, ab = values.get("P(A)"), values.get("P(B)"), values.get("P(A∩B)")
    union, cond = values.get("P(A∪B)"), values.get("P(A|B)")
    if exclusive and ab is None:
        ab = 0.0
    if independent:
        if a is None and cond is not None:
            a = cond                          # independent events have P(A|B) = P(A)
        if a is None and b is None and None not in (ab, union):
            # P(A) and P(B) are the two roots of t^2 - (P(A∪B) + P(A∩B))t + P(A∩B) = 0
            total, product = union + ab, ab
            disc = total * total - 4 * product
            if disc < -1e-12:
                return False
            a = (total + math.sqrt(max(disc, 0.0))) / 2      # the larger root is computed stably,
            if a > 1 + SMALLEST:                             # (near a double root, disc loses digits)
                return False
            a = min(a, 1.0)
            b = product / a if a > 0 else 0.0                # and the smaller one from a·b = P(A∩B)
        # With P(A) and P(B) both unknown and nothing else to pin them, P(A) = P(A∩B) / P(B) can
        # always be met, so independence adds no further condition.

    rows = []                                 # ((p, q, r), s) means p·P(A) + q·P(B) + r·P(A∩B) <= s

    def at_most(p, q, r, s):
        rows.append(((p, q, r), s))

    def equal(p, q, r, s, tol):
        at_most(p, q, r, s + tol)
        at_most(-p, -q, -r, -s + tol)

    known = [a, b, ab]
    free = [i for i in range(3) if known[i] is None]
    for i in free:
        unit = [1 if j == i else 0 for j in range(3)]
        at_most(*[-x for x in unit], 0)               # at least 0
        at_most(*unit, 1)                             # at most 1
    at_most(-1, 0, 1, 0)                              # P(A∩B) <= P(A)
    at_most(0, -1, 1, 0)                              # P(A∩B) <= P(B)
    at_most(1, 1, -1, 1)                              # P(A∪B) = P(A) + P(B) - P(A∩B) <= 1
    if union is not None:
        equal(1, 1, -1, union, slack(union))
    if cond is not None:                              # P(A∩B) = P(A|B)P(B), within slack·P(B)
        at_most(0, -cond - slack(cond), 1, 0)
        at_most(0, cond - slack(cond), -1, 0)
    if independent and a is not None:
        equal(0, a, -1, 0, 0.0)                       # P(A∩B) = P(A)P(B) once P(A) is known
    elif independent and b is not None:
        equal(b, 0, -1, 0, 0.0)
    reduced = [([coef[i] for i in free], s - sum(coef[i] * known[i] for i in range(3) if known[i] is not None))
               for coef, s in rows]
    corners = _corners(reduced, len(free))
    if not corners:
        return False
    if cond is not None and b is None:                # P(B) > 0 somewhere, so at some corner
        return max(c[free.index(1)] for c in corners) > 1e-12
    return cond is None or b > 0


def _corners(rows, k):
    """Every point where k of the planes meet and all the inequalities hold (k unknowns, 0 to 3)."""
    def ok(x):
        return all(sum(p * xi for p, xi in zip(coef, x)) <= s + 1e-12 for coef, s in rows)
    if k == 0:
        return [[]] if ok([]) else []
    found = []
    for chosen in itertools.combinations(rows, k):
        x = _solve([coef for coef, s in chosen], [s for coef, s in chosen])
        if x is not None and ok(x):
            found.append(x)
    return found


def _solve(m, rhs):
    """Solve the k x k system m·x = rhs by Gaussian elimination; None if it has no single solution."""
    k = len(m)
    a = [list(row) + [r] for row, r in zip(m, rhs)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(k):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    return [a[i][k] / a[i][i] for i in range(k)]


def parse(question):
    q = question or ""
    rest = q
    values, unreadable = {}, []
    for key, pattern in (("P(A∩B)", JOINT), ("P(A|B)", COND), ("P(A∪B)", UNION),
                         ("P(A)", SINGLE["P(A)"]), ("P(B)", SINGLE["P(B)"])):
        seen = []
        v, rest = _grab(pattern, rest)
        while v is not None:                  # the same value may be given twice; read every one
            seen.append(v)
            v, rest = _grab(pattern, rest)
        if not seen:
            continue
        if not all(math.isfinite(x) for x in seen):
            unreadable.append("%s is not a number I can use (for example, 1/0)." % key)
        elif any(x != seen[0] for x in seen):
            unreadable.append("%s is given more than once, with different values (%s)."
                              % (key, ", ".join(_n(x) for x in seen)))
        else:
            values[key] = seen[0]             # kept exact: 1/3 must stay 1/3 for the checks
    for key, pattern in (("P(A∩B)", JOINT), ("P(A|B)", COND), ("P(A∪B)", UNION),
                         ("P(A)", SINGLE["P(A)"]), ("P(B)", SINGLE["P(B)"])):
        # a value that starts like a number but could not be read whole: "0,3", "0.5/2", "0.3and"
        for m in re.finditer("(?:%s)\\s*%s\\s*([-+.\\d][^\\s;!?)]*)" % (pattern, SAYS), rest, flags=re.I):
            raw = m.group(1).rstrip(".,")
            hint = ("write decimals with a point, for example 0.3 rather than 0,3" if re.match(r"-?\d+,\d", raw)
                    else "please type a number such as 0.3, 30% or 1/3")
            unreadable.append("I couldn't read the value given for %s (%s): %s." % (key, raw, hint))

    low = q.lower()
    negated = bool(re.search(NOT_EXCLUSIVE, low))
    exclusive = bool(re.search(r"mutually exclusive|disjoint|\bexclusive\b", low)) and not negated
    asked_exclusive = bool(re.search(ASKED_EXCLUSIVE, low))
    independent = "independen" in low
    dependent = bool(re.search(r"\bdependent\b", low))
    not_dependent = bool(re.search(NOT_DEPENDENT, low))
    about_independence = independent or dependent                  # for the question type only
    not_independent = bool(re.search(NOT_INDEPENDENT, low)) or (dependent and not not_dependent)
    states_independent = (independent and not not_independent) or not_dependent
    asked_independent = bool(re.search(ASKED_INDEPENDENT, low))
    # Notation is looked for in rest, where the given values have been removed: "P(A|B)=0.3" is a given,
    # not a question about P(A|B). "given B" asks for a conditional; "given P(A)=0.3" does not.
    conditional = (bool(re.search(COND, rest, flags=re.I))
                   or bool(re.search(r"\bgiven\s+(?:that\s+)?b\b|conditional", low)))
    union = bool(re.search(UNION, rest, flags=re.I)) or bool(re.search(r"addition rule|\bunion\b|\beither\b", low))
    other_events = bool(_named_events(q) - {"A", "B"})
    unsupported = bool(re.search(UNSUPPORTED, q, flags=re.I))

    target = None
    m = re.search(TARGET, rest, flags=re.I)        # values were removed from rest, so P(X)=0.3 never counts
    if m:
        expr = (m.group(1) or m.group(2)).strip()
        for name, pattern in (("intersection", JOINT), ("conditional", COND), ("union", UNION)):
            if re.fullmatch(pattern, expr, flags=re.I):
                target = name
    else:
        for name, pattern in WORD_TARGET:
            if re.search(pattern, low):
                target = name
                break

    # What is asked decides the question; what is stated is a given.
    if other_events or unsupported:
        qtype = "other"                                 # two events, A and B, and five quantities only
    elif target:
        qtype = target                                  # an explicit "What is P(...)?"
    elif asked_independent and exclusive and not asked_exclusive:
        qtype = "exclusive_and_independent"             # "A and B are mutually exclusive. Are they independent?"
    elif asked_exclusive and not asked_independent:
        qtype = "exclusive"                             # "A and B are independent. Are they mutually exclusive?"
    elif asked_independent:
        qtype = "independence"
    elif exclusive and about_independence:
        qtype = "exclusive_and_independent"             # "Can mutually exclusive events be independent?"
    elif independent and not re.search(NOT_INDEPENDENT, low):
        qtype = "independence"
    elif conditional:
        qtype = "conditional"
    elif union:
        qtype = "union"
    elif exclusive:
        qtype = "exclusive"
    else:
        qtype = "other"
    # A property the student asks about is not a given; a stated one is.
    if qtype == "exclusive":
        exclusive = False
    indep_given = (qtype in ("union", "conditional", "intersection", "exclusive") and states_independent
                   and not asked_independent)
    # A stated "not ..." is a given too, and the values must not contradict it; asked, it is the question.
    # Any question about the property ("Are mutually exclusive events always dependent?") counts as asked.
    def questioned(words):
        clause = r"(?:[^.?!]|\.(?=\d))*"                  # a decimal point does not end the sentence
        return bool(re.search(r"\b(?:are|is|can|could)\b%s\b(?:%s)\b%s\?" % (clause, words, clause), low))
    not_excl_given = negated and not asked_exclusive and not questioned("mutually exclusive|disjoint")
    not_indep_given = not_independent and not asked_independent and not questioned("(?:in)?dependent")

    specific = (bool(re.search(r"\b" + PR + r"[AB]", q, flags=re.I)) or bool(re.search(r"\ba\s+and\s+b\b", low))
                or bool(re.search(r"\ba\s+(?:\w+\s+)?(?:in)?dependent\s+(?:of|from)\s+b\b", low)))
    generic = bool(re.search(r"\bevents?\b", q, flags=re.I))
    pronoun = bool(re.search(PRONOUN, low))
    referent_clear = specific or generic or not pronoun

    if other_events or unsupported:
        problems = []          # nothing is checked for a question outside A and B, so its values are not either
    else:
        problems = unreadable + check_values(values, exclusive, indep_given,
                                             not_exclusive=not_excl_given, not_independent=not_indep_given)

    return {"question_type": qtype,
            "question_label": TYPES[qtype],
            "events": ("A, B and other events (only A and B are covered)" if other_events
                       else "A and B (complements and P(B|A) are not covered)" if unsupported
                       else "A and B" if specific else ("any two events" if referent_clear
                                                        else "unclear (\"%s\")" % re.search(PRONOUN, low).group(1)))
                      + (" · stated not mutually exclusive" if negated else "")
                      + (" · stated not independent" if not_independent else ""),
            "referent_clear": referent_clear,
            "mutually_exclusive": exclusive,
            "independent": indep_given,
            "not_mutually_exclusive": not_excl_given,
            "not_independent": not_indep_given,
            "values": values,
            "problems": problems}


def from_fields(fields):
    """Build an interpretation from the correction form: the student's edit replaces the inference."""
    qtype = fields.get("question_type")
    qtype = qtype if isinstance(qtype, str) and qtype in TYPES else "other"
    values = {}
    problems = []
    given = fields.get("values")
    given = given if isinstance(given, dict) else {}
    for key in ("P(A)", "P(B)", "P(A∩B)", "P(A|B)", "P(A∪B)"):
        raw = str(given.get(key, "")).strip()
        if raw:
            try:
                v = _value(raw)
            except (ValueError, ZeroDivisionError, decimal.InvalidOperation):
                v = float("nan")
            if math.isfinite(v):          # rejects NaN, inf and 1/0, which JSON cannot carry
                values[key] = v
            else:
                problems.append("%s must be a number such as 0.2." % key)
    # "Are A and B mutually exclusive?" asks about the property, so it is never taken as given there.
    exclusive = qtype == "exclusive_and_independent" or (qtype != "exclusive" and bool(fields.get("mutually_exclusive")))
    independent = qtype in ("union", "conditional", "intersection", "exclusive") and bool(fields.get("independent"))
    # A stated "not mutually exclusive" or "not independent" stays a given when the form is resubmitted
    not_exclusive = qtype != "exclusive" and fields.get("not_mutually_exclusive") is True
    not_independent = qtype != "independence" and fields.get("not_independent") is True
    ticked_both = ((["A and B cannot be both mutually exclusive and not mutually exclusive: untick one."]
                    if exclusive and not_exclusive else [])
                   + (["A and B cannot be both independent and not independent: untick one."]
                      if independent and not_independent else []))
    interp = {"question_type": qtype, "question_label": TYPES[qtype],
              "events": "A and B" + (" · stated not mutually exclusive" if not_exclusive else "")
                        + (" · stated not independent" if not_independent else ""),
              "referent_clear": True, "mutually_exclusive": exclusive, "independent": independent,
              "not_mutually_exclusive": not_exclusive, "not_independent": not_independent,
              "values": values, "problems": problems, "corrected": True}
    interp["problems"] += ticked_both or check_values(values, exclusive, independent,
                                                      not_exclusive=not_exclusive, not_independent=not_independent)
    return interp


if __name__ == "__main__":
    print(json.dumps(parse(" ".join(sys.argv[1:]) or "Are they independent? I don't have the numbers."),
                     ensure_ascii=False, indent=1))
