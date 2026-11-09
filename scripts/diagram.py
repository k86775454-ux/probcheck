"""Draw docs/diagram/system_diagram.svg by hand-placed coordinates (graphviz layout was unreadable at A4)."""
import os
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "diagram", "system_diagram.svg")
W, H = 1720, 960
S = []
STY = {"impl": ('#e8f1f8', '#1f5f8b', ''), "gate": ('#e6f3ec', '#1e6b45', ''),
       "sim": ('#fff1e0', '#c46a00', 'stroke-dasharray="7 4"'), "plan": ('#f3f4f6', '#8a96a3', 'stroke-dasharray="2 4"'),
       "file": ('#ffffff', '#5b6673', '')}
def esc(t): return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def box(x, y, w, h, lines, kind="impl", bold_first=True, size=13, anchor="middle"):
    f, c, d = STY[kind]
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{f}" stroke="{c}" stroke-width="1.8" {d}/>')
    lh = size + 4; y0 = y + h / 2 - (len(lines) - 1) * lh / 2 + size / 3
    tx = x + w / 2 if anchor == "middle" else x + 10
    col = "#5b6673" if kind == "plan" else "#17202b"
    for i, t in enumerate(lines):
        wt = "700" if (i == 0 and bold_first) else "400"
        S.append(f'<text x="{tx}" y="{y0 + i * lh}" font-size="{size if i == 0 else size - 1}" font-weight="{wt}" text-anchor="{anchor}" fill="{col}">{esc(t)}</text>')
def cluster(x, y, w, h, label):
    S.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="none" stroke="#9fb3c4" stroke-width="1.5"/>')
    S.append(f'<text x="{x + 12}" y="{y + 20}" font-size="13" font-weight="700" fill="#5b6673">{esc(label)}</text>')
def arrow(pts, label=None, lx=None, ly=None, kind="impl", both=False, anchor="middle"):
    col = {"impl": "#4a5562", "gate": "#1e6b45", "plan": "#8a96a3", "sim": "#c46a00"}[kind]
    dash = {"plan": 'stroke-dasharray="2 4"', "gate": 'stroke-dasharray="6 4"'}.get(kind, "")
    p = " ".join(f"{a},{b}" for a, b in pts)
    m = f'marker-end="url(#a_{kind})"' + (f' marker-start="url(#s_{kind})"' if both else "")
    S.append(f'<polyline points="{p}" fill="none" stroke="{col}" stroke-width="1.6" {dash} {m}/>')
    if label:
        for i, t in enumerate(label.split("\n")):
            S.append(f'<text x="{lx}" y="{ly + i * 13}" font-size="11" text-anchor="{anchor}" fill="{col}" '
                     f'stroke="#ffffff" stroke-width="4" paint-order="stroke">{esc(t)}</text>')

# clusters
cluster(170, 30, 1540, 190, "Browser · index.html")
cluster(170, 250, 1540, 330, "Server · app.py (Python standard library)")
cluster(600, 610, 640, 150, "Local data")
# student
S.append('<ellipse cx="85" cy="130" rx="62" ry="28" fill="#fff7d6" stroke="#b38600" stroke-width="1.8"/>')
S.append('<text x="85" y="135" font-size="14" font-weight="700" text-anchor="middle">Student</text>')
# browser
box(190, 60, 250, 130, ["Question box", "example question chips", "“What I can / can't check”"])
box(470, 50, 700, 160, ["Response card", "verbal uncertainty cue (icon + label + first-person sentence)",
                        "What I understood · sentences with one-click § source",
                        "calculation (code) · removed sentences + reasons",
                        "dated passages · SUPERSEDED label · match score"])
box(1200, 60, 490, 130, ["Controls", "Correct these details · clarify options",
                         "This source doesn't support it", "Add revision slot · Confirm / Cancel"])
# lane A
xs = [190, 380, 570, 760, 950, 1140, 1330]; y, w, h = 300, 150, 92
box(xs[0], y, w, h, ["parse.py", "interpretation:", "type, events,", "values, problems"])
box(xs[1], y, w, h, ["Gate", "act / ask / decline", "repair turns", "(no model call)"], kind="gate")
box(xs[2], y, w, h, ["checker.py", "arithmetic and", "conditions in code;", "facts + rule ids"])
box(xs[3], y, w, h, ["Rule lookup", "each fact needs a", "current passage", "in its section"])
box(xs[4], y, w, h, ["Context", "instructions · notes ·", "checked facts ·", "question; logged"])
box(xs[5], y, w, h, ["Language model", "mock words the", "checked facts;", "overclaim switch"], kind="sim")
box(xs[6], y, w, h, ["verify.py", "per sentence: source", "shown, current, numbers", "traceable, wording"])
box(xs[5], 450, w, 70, ["Live LLM endpoint", "wired, not evaluated"], kind="plan")
# right column
box(1510, 290, 180, 54, ["Report + recheck", "never retrains"])
box(1510, 356, 180, 40, ["feedback_log.jsonl"], kind="file", bold_first=False, size=12)
box(1510, 420, 180, 70, ["book_slot tool", "validate → confirm", "→ run → log"])
box(1510, 504, 180, 44, ["schedule.json", "tool_log.jsonl"], kind="file", bold_first=False, size=12)
# data
box(760, 650, 160, 80, ["retrieve.py", "lexical score +", "superseded rerank"])
box(960, 645, 260, 92, ["Sample probability notes", "5 files · 11 passages", "source · section · date", "(written for this project)"], kind="file")
# planned band
box(190, 800, 300, 62, ["Planned: model-based", "question interpretation (+ same correction)"], kind="plan")
box(760, 800, 460, 62, ["Planned: real course notes with embedding retrieval;", "user study of error detection and reliance"], kind="plan")
box(1510, 800, 180, 62, ["Planned: tutor review", "of feedback_log reports"], kind="plan")

# arrows
arrow([(147, 128), (186, 125)], "types / picks", 166, 112)
arrow([(820, 50), (820, 16), (85, 16), (85, 98)], "reads cue, checks source", 450, 12)
arrow([(110, 104), (110, 24), (1640, 24), (1640, 56)], "corrects · reports · confirms", 1340, 20)
arrow([(315, 190), (315, 296)], "question", 322, 292, anchor="start")
arrow([(1230, 190), (1230, 236), (270, 236), (270, 296)], "corrected fields", 1150, 232)
arrow([(455, 300), (500, 214)], "clarify · fix values · decline", 512, 262, kind="gate", anchor="start")
for i, lab in enumerate(["interp.", "in scope", "rule ids", "facts", "context", "JSON"]):
    x1 = xs[i] + w; x2 = xs[i + 1]
    arrow([(x1, 346), (x2 - 4, 346)], lab, (x1 + x2) / 2, 338)
arrow([(1405, 300), (1405, 250), (1120, 250), (1120, 214)], "verified sentences + removed list", 1262, 246)
S.append('<polyline points="645,392 645,420 1100,420" fill="none" stroke="#4a5562" stroke-width="1.6"/>')
arrow([(1100, 420), (1405, 420), (1405, 396)], "numbers for the check", 1250, 433)
arrow([(835, 392), (835, 646)], "rule query ↓  passage + id ↑\n(score ≥ 0.25)", 845, 600, both=True, anchor="start")
arrow([(920, 690), (956, 690)])
arrow([(1025, 392), (1025, 485), (1136, 485)], None, kind="plan")
arrow([(1290, 485), (1405, 485), (1405, 396)], None, kind="plan")
arrow([(1600, 190), (1600, 286)], "report i ↓ result ↑", 1590, 270, both=True, anchor="end")
arrow([(1600, 344), (1600, 352)])
arrow([(1690, 190), (1704, 190), (1704, 455), (1694, 455)], "propose /\nconfirm ↕", 1700, 405, both=True, anchor="end")
arrow([(1600, 490), (1600, 500)])
arrow([(265, 392), (265, 796)], None, kind="plan")
# legend
ly = 905
items = [("impl", "Implemented"), ("gate", "Implemented: fixed repair turn"), ("sim", "Simulated (mock model)"),
         ("plan", "Planned / not evaluated"), ("file", "Local file")]
x = 190
for k, t in items:
    f, c, d = STY[k]
    S.append(f'<rect x="{x}" y="{ly}" width="34" height="20" rx="5" fill="{f}" stroke="{c}" stroke-width="1.8" {d}/>')
    S.append(f'<text x="{x + 42}" y="{ly + 15}" font-size="13" fill="#17202b">{t}</text>'); x += 42 + len(t) * 7.4 + 30

defs = "".join(f'<marker id="a_{k}" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,1 L9,5 L0,9 z" fill="{c}"/></marker>'
               f'<marker id="s_{k}" markerWidth="10" markerHeight="10" refX="2" refY="5" orient="auto"><path d="M9,1 L0,5 L9,9 z" fill="{c}"/></marker>'
               for k, c in {"impl": "#4a5562", "gate": "#1e6b45", "plan": "#8a96a3", "sim": "#c46a00"}.items())
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="DejaVu Sans, Helvetica, Arial, sans-serif"><defs>{defs}</defs>'
       f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + "".join(S) + "</svg>")
open(OUT, "w", encoding="utf-8").write(svg); print(OUT)
