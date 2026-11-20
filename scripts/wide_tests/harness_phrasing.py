"""Wide test 3: many phrasings of each question. The typed question must be read the same way as the
correction form filled in with the true reading, and give the same outcome.

    python scripts/wide_tests/harness_phrasing.py ."""
import contextlib, io, math, os, random, sys, tempfile
from unittest.mock import patch

ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
import app, tools  # noqa: E402
tmp = tempfile.mkdtemp()
for mod, name in ((app, "FEEDBACK_LOG"), (app, "CONTEXT_LOG"), (tools, "LOG"), (tools, "SCHEDULE")):
    patch.object(mod, name, os.path.join(tmp, name)).start()


def handle(payload):
    with contextlib.redirect_stdout(io.StringIO()):
        return app.handle(payload)


ASK = {
    "union": ["What is P(A∪B)?", "Find P(A or B).", "P(A∪B)?", "What is the probability of A or B?",
              "Compute P(A u B).", "Calculate the probability that either A or B occurs.", "Work out P(A ∪ B).",
              "P(A∪B) = ?", "What is Pr(A ⋃ B)?", "Find P(A union B)."],
    "intersection": ["What is P(A∩B)?", "Find P(A and B).", "What is the probability of both A and B?",
                     "P(A n B)?", "What is the probability that A and B both occur?", "Find P(AB).",
                     "P(A∩B)=?", "What is Pr(A ⋂ B)?", "Find P(A intersect B)."],
    "conditional": ["What is P(A|B)?", "Find P(A|B).", "What is the probability of A given B?",
                    "What is the probability of A given that B occurred?", "P(A|B)?", "Compute P(A | B).",
                    "P(A|B) = ?", "What is Pr(A|B)?"],
    "independence": ["Are A and B independent?", "Are the events independent?", "Are A and B dependent?",
                     "Is A independent of B?", "Are these two events independent?", "Independent?"],
    "exclusive": ["Are A and B mutually exclusive?", "Are A and B disjoint?", "Are the two events mutually exclusive?",
                  "Can A and B be mutually exclusive?", "Are they mutually exclusive?"],
}
PREMISE = {"none": [""], "excl": ["A and B are mutually exclusive. ", "Assume A and B are disjoint. ",
                                  "Given that A and B are mutually exclusive, "],
           "indep": ["A and B are independent. ", "Assume A and B are independent. ",
                     "Given that A and B are independent, "],
           "not": ["A and B are not mutually exclusive. ", "A and B aren't independent. "]}
NAMES = {"P(A)": ["P(A)", "Pr(A)", "P( A )"], "P(B)": ["P(B)", "Pr(B)"],
         "P(A∩B)": ["P(A∩B)", "P(A and B)", "P(A n B)", "P(A ⋂ B)", "P(A intersect B)", "P(AB)", "Pr(A∩B)"],
         "P(A∪B)": ["P(A∪B)", "P(A or B)", "P(A ⋃ B)", "P(A union B)", "Pr(A∪B)"], "P(A|B)": ["P(A|B)", "Pr(A | B)"]}
SAYS = ["=", " = ", " is ", ": ", " equals "]


def written(x):
    """x as a student might type it, and the value that text stands for (computed independently)."""
    style = random.choice(["plain", "plain", "percent", "percent word", "dot", "zeros", "fraction"])
    t = repr(x)
    if style == "percent":
        t = "%s%%" % repr(round(x * 100, 6)).rstrip("0").rstrip(".")
    elif style == "percent word":
        t = "%s percent" % repr(round(x * 100, 6)).rstrip("0").rstrip(".")
    elif style == "dot" and t.startswith("0."):
        t = t[1:]
    elif style == "zeros" and "." in t:
        t = t + "00"
    elif style == "fraction":
        from fractions import Fraction
        f = Fraction(t).limit_denominator(1000)
        if float(f) == x and f.denominator > 1:
            t = "%d/%d" % (f.numerator, f.denominator)
    if t.endswith("%"):
        return t, float(t[:-1]) / 100
    if t.endswith(" percent"):
        return t, float(t[:-8]) / 100
    if "/" in t:
        n, m = t.split("/")
        return t, int(n) / int(m)
    return t, float(t)

KEYS = ("P(A)", "P(B)", "P(A∩B)", "P(A∪B)", "P(A|B)")
random.seed(int(os.environ.get("SEED", 5)))   # SEED=n to try other cases
fails, n = [], 0
for _ in range(int(os.environ.get("CASES", 20000))):
    qtype = random.choice(list(ASK))
    premise = random.choice(list(PREMISE))
    if (qtype, premise) in (("exclusive", "excl"), ("independence", "indep")):
        continue
    a, b = round(random.random(), 2), round(random.random(), 2)
    if premise == "excl":
        b = round(min(b, 1 - a), 2)
        ab = 0.0
    elif premise == "indep":
        ab = a * b
    else:
        ab = round(random.uniform(max(0, a + b - 1), min(a, b)), 3)
    full = {"P(A)": a, "P(B)": b, "P(A∩B)": ab, "P(A∪B)": a + b - ab, "P(A|B)": ab / b if b else None}
    asked = {"union": "P(A∪B)", "intersection": "P(A∩B)", "conditional": "P(A|B)"}.get(qtype)
    keys = [k for k in KEYS if k != asked and full[k] is not None and random.random() < 0.6]
    typed = {k: written(round(full[k], 4)) for k in keys}
    vals = {k: typed[k][1] for k in keys}
    givens = ", ".join("%s%s%s" % (random.choice(NAMES[k]), random.choice(SAYS), typed[k][0]) for k in keys)
    lead = random.choice(PREMISE[premise])
    ask = random.choice(ASK[qtype])
    if lead.startswith("Given that"):
        ask = ask[0].lower() + ask[1:]
    if not givens:
        q = lead + ask
    elif random.random() < 0.5:
        q = lead + givens + ". " + (ask[0].upper() + ask[1:])
    else:
        q = "Given " + givens + ", " + (lead[0].lower() + lead[1:] if lead else "") + ask[0].lower() + ask[1:]
    if random.random() < 0.15:
        q = q.lower()
    want_type = "exclusive_and_independent" if (qtype == "independence" and premise == "excl") else qtype
    want_excl = premise == "excl" and want_type != "exclusive"
    want_indep = premise == "indep" and want_type in ("union", "conditional", "intersection", "exclusive")
    d = handle({"action": "ask", "message": q})
    n += 1
    i = d["interpretation"]
    # a stated "not ..." must be rejected when the typed values fix P(A∩B) and contradict it
    va, vb, vab = vals.get("P(A)"), vals.get("P(B)"), vals.get("P(A∩B)")
    if vab is None and None not in (va, vb) and (min(va, vb) == 0 or max(va, vb) == 1):
        vab = min(va, vb) if max(va, vb) == 1 else 0.0
    contradicts = premise == "not" and vab is not None and (
        ("mutually exclusive" in lead and qtype != "exclusive" and vab == 0)
        or ("independent" in lead and qtype != "independence" and None not in (va, vb)
            and math.isclose(vab, va * vb, rel_tol=1e-9, abs_tol=0.0)))
    if contradicts:
        if d["status"] != "invalid":
            fails.append(("contradicted 'not' premise accepted", q, d["status"]))
        continue
    got = (i["question_type"], bool(i["mutually_exclusive"]), bool(i["independent"]))
    if (got != (want_type, want_excl, want_indep) or set(i["values"]) != set(vals)
            or any(abs(i["values"][k] - vals[k]) > 1e-12 for k in vals)):
        fails.append(("misread", q, got, (want_type, want_excl, want_indep), i["values"], vals))
        continue
    form = {"question_type": want_type, "mutually_exclusive": want_excl, "independent": want_indep,
            "values": {k: typed[k][0] if k in vals else "" for k in KEYS}}
    if not vals and not lead and ("they" in ask.lower() or "events" in ask.lower() or ask == "Independent?"):
        continue                    # no events named and no numbers: asking which events, or the definition, is right
    d2 = handle({"action": "correct", "fields": form})
    if (d["status"], d.get("verdict")) != (d2["status"], d2.get("verdict")):
        fails.append(("outcome differs from the form", q, (d["status"], d.get("verdict")), (d2["status"], d2.get("verdict"))))
    if d["status"] == "invalid":
        fails.append(("consistent values rejected", q, d["needs"]))
print("cases:", n, "failures:", len(fails))
groups = {}
for f in fails:
    groups.setdefault(f[0], []).append(f)
for k, v in groups.items():
    print("\n==", k, "x", len(v))
    seen = set()
    for f in v:
        key = str(f[2:4])
        if key in seen:
            continue
        seen.add(key)
        print("   ", f[1:])
        if len(seen) >= 12:
            break
