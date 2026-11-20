"""Wide test 4: compare parse.check_values with oracle.py on random value sets, with and without the
"mutually exclusive", "independent", "not mutually exclusive" and "not independent" premises.

    python scripts/wide_tests/stress_values.py . SEED CASES

A third of the sets come from real probability models, a third are random, and a third are built
around the edges: probabilities of 0 and 1, very small ones, and values just outside their range
because of rounding. Sets that only rounding separates from possible (oracle.consistent is None) are
not counted either way."""
import collections, math, os, random, sys
sys.path.insert(0, sys.argv[1])
sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import parse

import oracle
from oracle import KEYS


def model(indep=False):
    """Values from a real probability model."""
    a, b = random.choice([random.random(), 0, 1]), random.random()
    low, high = max(0, a + b - 1), min(a, b)
    ab = a * b if indep else random.choice([low, high, random.uniform(low, high)])
    vals = {"P(A)": a, "P(B)": b, "P(A∩B)": ab, "P(A∪B)": a + b - ab, "P(A|B)": ab / b if b else None}
    return vals, ab == 0


def edge():
    """Values chosen around the edges, where the earlier oracle and checks were weakest."""
    pick = lambda: random.choice([0, 0, 1, 1, 0.5, 1e-7, 1e-8, 3e-9, random.random(), random.random() ** 6,
                                  1 - random.random() ** 6, round(random.random(), 1)])
    return {k: pick() for k in KEYS}


random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
fails = collections.Counter(); examples = {}
N = int(sys.argv[3]) if len(sys.argv) > 3 else 100000
counted = 0
for i in range(N):
    indep = random.random() < 0.3
    kind = random.random()
    if kind < 1 / 3:
        full, is_excl = model(indep)
        digits = random.choice([2, 3, 4, 6, 12])
        excl = is_excl and random.random() < 0.5
    elif kind < 2 / 3:
        full = {k: random.choice([0, 1, random.random(), random.random() ** 3]) for k in KEYS}
        digits = random.choice([1, 2, 3])
        excl = random.random() < 0.2
    else:
        full, digits = edge(), 12
        excl = random.random() < 0.2
    keys = [k for k in KEYS if full[k] is not None and random.random() < 0.55]
    v = {k: round(full[k], digits) if full[k] >= 1e-6 else full[k] for k in keys}
    if random.random() < 0.15 and v:             # nudge one value
        k = random.choice(list(v)); v[k] = round(min(1, max(0, v[k] + random.choice([-1, 1]) * 10 ** -random.randint(1, 4))), 6)
    # a stated "not ..." premise: possible exactly when the model with that premise exists
    not_excl = not_indep = False
    if random.random() < 0.1 and not excl:
        not_excl = True                          # a stated premise and its negation never come together
    elif random.random() < 0.1 and not indep:
        not_indep = True
    got = parse.check_values(dict(v), exclusive=excl, independent=indep,
                             not_exclusive=not_excl, not_independent=not_indep)
    ok = oracle.consistent(v, excl, indep)
    if (not_excl or not_indep) and ok:
        # the oracle has no "not" premises; judge the plain cases where the values fix P(A∩B) exactly
        a, b, ab = v.get("P(A)"), v.get("P(B)"), v.get("P(A∩B)")
        if ab is None and None not in (a, b) and (min(a, b) == 0 or max(a, b) == 1):
            ab = min(a, b) if max(a, b) == 1 else 0.0
        if ab is None and excl:
            ab = 0.0
        if ab is None:
            continue
        if not_excl and ab == 0:
            ok = False
        elif not_indep and None not in (a, b) and math.isclose(ab, a * b, rel_tol=1e-9, abs_tol=0.0):
            ok = False
    if ok is None:
        continue
    counted += 1
    label = ",".join(k for k in KEYS if k in v) + (" excl" if excl else "") + (" indep" if indep else "") + \
        (" not-excl" if not_excl else "") + (" not-indep" if not_indep else "")
    if ok and got:
        tag = "rejected consistent " + label
    elif not ok and not got:
        tag = "accepted impossible " + label
    else:
        continue
    fails[tag] += 1
    examples.setdefault(tag, (v, got))
print("cases:", N, "judged:", counted, "disagreements:", sum(fails.values()))
for tag, n in fails.most_common():
    print(n, tag, examples[tag])
