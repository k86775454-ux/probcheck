"""Independent ground truth for the test harnesses: is there a probability model with these values?

Written separately from ProbCheck's own checks and computed exactly, with fractions rather than
floating point. The unknowns are (P(A), P(B), P(A∩B)); every rule is linear in them once the known
values are put in, so the allowed points form a polytope, and it is non-empty exactly when one of its
corners satisfies every rule. P(A|B) needs P(B) > 0, which holds somewhere exactly when it holds at
a corner (P(B) is largest at a corner).

Values are read as the decimals they print as (0.1 is 1/10), which is how a student typed them.
strict: exact (no allowance at all). loose: P(A∪B) and P(A|B) may be off by 5e-4 because a student
rounded them, and the other rules may be off by floating-point noise (1e-12, or 1e-9 for the product
P(A)P(B)). A value set that is possible strictly must be accepted, and one that is impossible even
loosely must be rejected; between the two, either is fine.

(An earlier version used SciPy's floating-point linear programming with P(B) >= 1e-9. Its tolerances
let P(A) = 0 with P(A|B) = 0.5 through, so it missed the same cases as ProbCheck; an outside review
found them.)
"""
import itertools
from fractions import Fraction as F

import numpy as np

KEYS = ("P(A)", "P(B)", "P(A∩B)", "P(A∪B)", "P(A|B)")
LOOSE = F(5, 10000)
NOISE, PRODUCT_NOISE = F(1, 10 ** 12), F(1, 10 ** 9)
SMALLEST = 1e-9          # ProbCheck declines positive probabilities below this; not judged here


def _solve(m, rhs):
    k = len(m)
    a = [list(row) + [r] for row, r in zip(m, rhs)]
    for col in range(k):
        pivot = next((r for r in range(col, k) if a[r][col] != 0), None)
        if pivot is None:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(k):
            if r != col and a[r][col] != 0:
                f = a[r][col] / a[col][col]
                a[r] = [x - f * y for x, y in zip(a[r], a[col])]
    return [a[i][k] / a[i][i] for i in range(k)]


def _corners(rows, k):
    def ok(x):
        return all(sum(p * xi for p, xi in zip(coef, x)) <= s for coef, s in rows)
    if k == 0:
        return [[]] if ok([]) else []
    out = []
    for chosen in itertools.combinations(rows, k):
        x = _solve([c for c, s in chosen], [s for c, s in chosen])
        if x is not None and ok(x):
            out.append(x)
    return out


def feasible(v, excl, tol, indep=False):
    """tol is 0 (strict) or LOOSE; v holds floats, which are read exactly."""
    tol = F(tol)
    noise, pnoise = (NOISE, PRODUCT_NOISE) if tol else (F(0), F(0))
    x = {k: (F(repr(float(v[k]))) if v.get(k) is not None else None) for k in KEYS}
    a, b, ab, u, c = (x[k] for k in KEYS)
    if any(not 0 <= val <= 1 for val in v.values()):
        return False
    if c is not None and b == 0:
        return False
    if indep and c is not None:                  # P(A|B) = P(A) for independent events with P(B) > 0
        if a is not None and abs(a - c) > tol:
            return False
        a = c if a is None else a
    if indep and a is None and b is None:
        if excl and ab is not None and ab > noise:
            return False
        abx = F(0) if excl and ab is None else ab
        if abx is not None and u is not None:    # P(A), P(B) are roots of t^2 - (u + ab)t + ab: scan P(A)
            A = np.linspace(0, 1, 200001); B = float(u) + float(abx) - A
            t = float(tol) + 1e-12
            ok = (B >= -t) & (B <= 1 + t) & (np.abs(A * B - float(abx)) <= t) & (float(abx) <= np.minimum(A, B) + t)
            return bool(ok.any())
        indep = False                            # nothing pins P(A) and P(B): independence can always hold
    known = [a, b, ab]
    free = [i for i in range(3) if known[i] is None]
    rows = []

    def le(coef, s):
        s2 = F(s) - sum(F(coef[i]) * known[i] for i in range(3) if known[i] is not None)
        rows.append(([F(coef[i]) for i in free], s2))

    for i in free:
        unit = [1 if j == i else 0 for j in range(3)]
        le([-q for q in unit], 0)
        le(unit, 1)
    le([-1, 0, 1], noise); le([0, -1, 1], noise); le([1, 1, -1], 1 + noise)
    if u is not None:
        le([1, 1, -1], u + tol + noise); le([-1, -1, 1], -u + tol + noise)
    if c is not None:
        le([0, -c - tol - noise, 1], 0); le([0, c - tol - noise, -1], 0)
    if excl:
        le([0, 0, 1], noise)
    if indep and a is not None:
        le([0, a, -1], pnoise); le([0, -a, 1], pnoise)
    elif indep and b is not None:
        le([b, 0, -1], pnoise); le([-b, 0, 1], pnoise)
    corners = _corners(rows, len(free))
    if not corners:
        return False
    if c is not None and b is None:
        return max(p[free.index(1)] for p in corners) > 0
    return True


def consistent(v, excl, indep=False):
    """True or False when the answer is clear; None when only rounding separates them, or when a
    positive value is below SMALLEST (ProbCheck declines those)."""
    if any(0 < val < SMALLEST for val in v.values()):
        return None
    if feasible(v, excl, 0, indep):
        return True
    if not feasible(v, excl, LOOSE, indep):
        return False
    return None
