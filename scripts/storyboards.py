"""Compose captured frames into storyboard images (docs/storyboards/)."""
import os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(HERE, "docs", "frames"); OUT = os.path.join(HERE, "docs", "storyboards")
os.makedirs(OUT, exist_ok=True)
font = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"Student": (31, 95, 139), "System": (70, 80, 92)}
W = 760  # frame width in the board

def board(name, title, frames, cols=2):
    tiles = []
    for i, (actor, caption, file) in enumerate(frames, 1):
        im = Image.open(os.path.join(F, file)).convert("RGB")
        im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
        head = 64
        t = Image.new("RGB", (W + 2, im.height + head + 2), "white")
        d = ImageDraw.Draw(t)
        d.rectangle([0, 0, W + 1, im.height + head + 1], outline=(200, 206, 213), width=2)
        d.rounded_rectangle([12, 14, 52, 50], 8, fill=COL[actor]); d.text((32, 32), str(i), font=font(22, True), fill="white", anchor="mm")
        d.text((64, 18), actor.upper(), font=font(15, True), fill=COL[actor])
        d.text((64, 38), caption, font=font(17), fill=(23, 32, 43))
        t.paste(im, (1, head + 1)); tiles.append(t)
    gap = 24; rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    width = cols * (W + 2) + (cols + 1) * gap; top = 70
    heights = [max(t.height for t in r) for r in rows]
    B = Image.new("RGB", (width, top + sum(heights) + gap * (len(rows) + 1)), (245, 246, 248))
    d = ImageDraw.Draw(B); d.text((gap, 22), title, font=font(26, True), fill=(23, 32, 43))
    y = top
    for r, h in zip(rows, heights):
        x = gap
        for t in r:
            B.paste(t, (x, y)); x += W + 2 + gap
        y += h + gap
    B.save(os.path.join(OUT, name)); print(name, B.size)

board("storyboard1_checked_answer.png", "Storyboard 1 · A checked answer the student can verify", [
    ("Student", "Asks with values; scope shown first", "f1_1_ask.png"),
    ("System", "Cue, interpretation, cited sentences, calculation", "f1_2_answer.png"),
    ("Student", "Clicks '§2.3 source' on sentence 3", "f1_3_source.png"),
    ("System", "Passage highlighted: words that matched", "f1_3b_passage.png"),
    ("System", "Proposes revision slot; arguments shown", "f1_4_confirm.png"),
    ("Student", "Confirms; result read from the tool", "f1_5_done.png")])
board("storyboard2_clarify_correct.png", "Storyboard 2 · An ambiguous question is clarified, not guessed", [
    ("System", "Unclear 'they': asks, offers three options", "f2_1_clarify.png"),
    ("Student", "Chooses to enter values; corrects details", "f2_2_correct.png"),
    ("System", "Checks the corrected values", "f2_3_checked.png")])
board("storyboard3_failure_recovery.png", "Storyboard 3 · Unsupported claims are caught and reported", [
    ("System", "Demo overclaim: two sentences removed", "f3_1_removed.png"),
    ("Student", "Reports sentence 3; system rechecks", "f3_2_report.png"),
    ("System", "Outside the notes: declines, hands over", "f3_3_decline.png")])
