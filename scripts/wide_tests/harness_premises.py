"""Wide test 2: stated premises (mutually exclusive / independent), every question type, fractions,
percentages and decimals, and resubmitting the correction form unchanged.

    python scripts/wide_tests/harness_premises.py .

Possible versus impossible values come from oracle.py; expected answers are computed here."""
import contextlib, io, json, math, os, random, sys, tempfile
from fractions import Fraction
from unittest.mock import patch

ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import oracle  # noqa: E402
import app, tools  # noqa: E402

tmp = tempfile.mkdtemp()
for mod, name in ((app, "FEEDBACK_LOG"), (app, "CONTEXT_LOG"), (tools, "LOG"), (tools, "SCHEDULE")):
    patch.object(mod, name, os.path.join(tmp, name)).start()

TOL = 5e-4
FAIL, COUNT = [], {"n": 0}


def handle(payload):
    with contextlib.redirect_stdout(io.StringIO()):
        d = app.handle(payload)
    json.dumps(d, allow_nan=False)
    COUNT["n"] += 1
    return d


def routes(v, excl, indep, skip=()):
    a, b, ab, u, c = (v.get(k) for k in ("P(A)", "P(B)", "P(A∩B)", "P(A∪B)", "P(A|B)"))
    r = []
    if ab is not None: r.append(("given", ab))
    if excl and "exclusive" not in skip: r.append(("exclusive", 0.0))
    if indep and a is not None and b is not None and "independent" not in skip: r.append(("independent", a * b))
    if u is not None and a is not None and b is not None and "union" not in skip: r.append(("union", a + b - u))
    if c is not None and b is not None and "conditional" not in skip: r.append(("conditional", c * b))
    if a is not None and b is not None and min(a, b) == 0: r.append(("bounds", 0.0))
    if a is not None and b is not None and max(a, b) == 1: r.append(("bounds", min(a, b)))
    return r


def expected(qtype, v, excl, indep):
    a, b = v.get("P(A)"), v.get("P(B)")
    if qtype == "union":
        r = routes(v, excl, indep, skip=("union",))
        return None if (a is None or b is None or not r) else a + b - r[0][1]
    if qtype == "conditional":
        r = routes(v, excl, indep, skip=("conditional",))
        if b == 0: return "undefined"
        if b is not None and r: return r[0][1] / b
        if b is None and indep and a is not None: return a          # P(A|B) = P(A), whenever P(B) > 0
        if b is None and r and r[0][1] == 0: return 0.0             # 0 / P(B), whenever P(B) > 0
        return None
    if qtype == "intersection":
        r = routes(v, excl, indep)
        return r[0][1] if r else None
    if qtype == "independence":
        r = routes(v, excl, False)
        if a is None or b is None or not r: return None
        return "independent" if math.isclose(a * b, r[0][1], rel_tol=1e-9, abs_tol=1e-15) else "not independent"
    if qtype == "exclusive":
        r = routes(v, False, indep)
        if r: return "mutually exclusive" if abs(r[0][1]) < 1e-9 else "not mutually exclusive"
        if a is not None and b is not None and a + b > 1: return "not mutually exclusive"
        return None
    if qtype == "exclusive_and_independent":
        if a is None or b is None: return None
        return "not independent" if a > 0 and b > 0 else "independent"
    return None


def check(tag, d, qtype, v, excl, indep, overclaim=False):
    st = d["status"]
    ok = oracle.consistent(v, excl, indep)
    if ok is None:
        return                      # only rounding separates possible from impossible
    if not ok:
        if st != "invalid":
            FAIL.append(("inconsistent values answered", tag, st, d.get("verdict")))
        return
    if st == "invalid":
        FAIL.append(("consistent values rejected", tag, d.get("needs")))
        return
    if not overclaim and d["removed"]:
        FAIL.append(("sentence removed without the demo", tag, [r["why"] for r in d["removed"]]))
    ids = {e["id"]: e for e in d["evidence"]}
    for s in d["sentences"]:
        if s["passage_id"] not in ids or ids[s["passage_id"]].get("superseded"):
            FAIL.append(("sentence cites a missing or old passage", tag, s["text"]))
    exp = expected(qtype, v, excl, indep)
    got = d.get("verdict")
    if exp is None:
        if got is not None:
            FAIL.append(("verdict without enough values", tag, got))
        if st == "checked" and d.get("steps"):
            pass
        return
    if st != "checked":
        FAIL.append(("not answered although answerable", tag, st, d.get("needs"), "expected", exp))
        return
    if isinstance(exp, float):
        try:
            if abs(float(got) - exp) > 6e-4:
                FAIL.append(("wrong number", tag, got, "expected", round(exp, 6)))
        except (TypeError, ValueError):
            FAIL.append(("non-numeric verdict", tag, got, "expected", exp))
    elif got != exp:
        FAIL.append(("wrong verdict", tag, got, "expected", exp))
    if not d["sentences"]:
        FAIL.append(("no sentence shown for an answer", tag))


ASK = {"union": "What is P(A∪B)?", "conditional": "What is P(A|B)?", "intersection": "What is P(A∩B)?",
       "independence": "Are A and B independent?", "exclusive": "Are A and B mutually exclusive?",
       "exclusive_and_independent": "Can mutually exclusive events be independent?"}
FR = [Fraction(0), Fraction(1, 10), Fraction(1, 6), Fraction(1, 5), Fraction(1, 4), Fraction(1, 3), Fraction(2, 5),
      Fraction(1, 2), Fraction(3, 5), Fraction(2, 3), Fraction(3, 4), Fraction(4, 5), Fraction(9, 10), Fraction(1)]


def text(x, style):
    if style == "frac" and x.denominator != 1:
        return "%d/%d" % (x.numerator, x.denominator)
    if style == "pct":
        return ("%s" % (float(x) * 100)).rstrip("0").rstrip(".") + "%"
    return repr(float(x)) if style == "dec" else str(round(float(x), 2))


random.seed(int(os.environ.get("SEED", 11)))   # SEED=n to try other cases
for _ in range(int(os.environ.get("CASES", 25000))):
    qtype = random.choice(list(ASK))
    excl = qtype == "exclusive_and_independent" or (qtype not in ("exclusive",) and random.random() < 0.2)
    indep = qtype in ("union", "conditional", "intersection", "exclusive") and not excl and random.random() < 0.25
    a, b = random.choice(FR), random.choice(FR)
    vals = {}
    if random.random() < 0.9: vals["P(A)"] = a
    if random.random() < 0.95: vals["P(B)"] = b
    if random.random() < 0.4: vals["P(A∩B)"] = random.choice([a * b, min(a, b), max(Fraction(0), a + b - 1), random.choice(FR)])
    if qtype != "union" and random.random() < 0.25: vals["P(A∪B)"] = random.choice([a + b - a * b, a + b, max(a, b), random.choice(FR)])
    if qtype != "conditional" and random.random() < 0.2: vals["P(A|B)"] = random.choice([a, random.choice(FR)])
    vals = {k: x for k, x in vals.items() if 0 <= x <= 1}
    style = random.choice(["frac", "dec", "short", "pct"])
    names = {"P(A)": "P(A)", "P(B)": "P(B)", "P(A∩B)": random.choice(["P(A∩B)", "P(A and B)"]),
             "P(A∪B)": random.choice(["P(A∪B)", "P(A or B)"]), "P(A|B)": "P(A|B)"}
    givens = ", ".join("%s=%s" % (names[k], text(x, style)) for k, x in vals.items())
    lead = ""
    if excl and qtype != "exclusive_and_independent": lead = random.choice(["A and B are mutually exclusive. ", "A and B are disjoint. "])
    if indep: lead = random.choice(["A and B are independent. ", "Assume A and B are independent. "])
    if not excl and not indep and random.random() < 0.15: lead = random.choice(["A and B are not mutually exclusive. ", "A and B are not independent. "])
    q = lead + givens + (". " if givens else "") + ASK[qtype]
    d = handle({"action": "ask", "message": q})
    i = d["interpretation"]
    seen_q = i["question_type"]
    want_q = qtype
    if qtype == "independence" and excl: want_q = "exclusive_and_independent"
    if seen_q != want_q:
        FAIL.append(("question type misread", q, seen_q, "wanted", want_q)); continue
    if bool(i.get("mutually_exclusive")) != (excl if qtype != "exclusive" else False) or bool(i.get("independent")) != indep:
        FAIL.append(("premise misread", q, i.get("mutually_exclusive"), i.get("independent"))); continue
    def typed(t):
        if t.endswith("%"): return float(t[:-1]) / 100
        if "/" in t:
            n, m = t.split("/"); return float(n) / float(m)
        return float(t)
    fv = {k: typed(text(x, style)) for k, x in vals.items()}
    if any(not math.isclose(i["values"].get(k, -1), x, rel_tol=1e-12, abs_tol=1e-12) for k, x in fv.items()) or len(i["values"]) != len(fv):
        FAIL.append(("values misread", q, i["values"])); continue
    if lead.startswith("A and B are not"):
        # a stated "not ..." must be rejected when the values fix P(A∩B) and contradict it
        va, vb, vab = fv.get("P(A)"), fv.get("P(B)"), fv.get("P(A∩B)")
        if vab is None and None not in (va, vb) and (min(va, vb) == 0 or max(va, vb) == 1):
            vab = min(va, vb) if max(va, vb) == 1 else 0.0
        asked_same = ("exclusive" in lead and seen_q == "exclusive") or ("independent" in lead and seen_q == "independence")
        if not asked_same and vab is not None and (
                ("exclusive" in lead and vab == 0)
                or ("independent" in lead and None not in (va, vb) and math.isclose(vab, va * vb, rel_tol=1e-9, abs_tol=0.0))):
            if d["status"] != "invalid":
                FAIL.append(("contradicted 'not' premise accepted", q, d["status"]))
            continue
    check(q, d, seen_q, fv, i.get("mutually_exclusive"), indep)
    # resubmitting the form unchanged must give the same outcome
    fields = {"question_type": seen_q, "mutually_exclusive": bool(i.get("mutually_exclusive")), "independent": bool(i.get("independent")),
              "values": {k: repr(i["values"][k]) if k in i["values"] else "" for k in ("P(A)", "P(B)", "P(A∩B)", "P(A∪B)", "P(A|B)")}}
    d2 = handle({"action": "correct", "fields": fields})
    if (d2["status"], d2.get("verdict")) != (d["status"], d.get("verdict")):
        FAIL.append(("form resubmission changed the outcome", q, (d["status"], d.get("verdict")), (d2["status"], d2.get("verdict"))))

print("cases run:", COUNT["n"])
print("FAILURES:", len(FAIL))
groups = {}
for f in FAIL:
    groups.setdefault(f[0], []).append(f)
for k, v in groups.items():
    print("\n==", k, "x", len(v))
    for f in v[:5]:
        print("   ", f[1:])
