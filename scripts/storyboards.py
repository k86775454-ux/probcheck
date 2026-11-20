"""Compose captured frames into storyboard images (docs/storyboards/)."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.path.join(HERE, "docs", "frames"); OUT = os.path.join(HERE, "docs", "storyboards")
os.makedirs(OUT, exist_ok=True)
font = lambda s, b=False: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if b else ""), s)
COL = {"Student": (31, 95, 139), "System": (70, 80, 92)}
# Development status of what each frame shows (same colours as the system diagram).
STATUS = {"impl": ("Implemented", (232, 241, 248), (31, 95, 139)),
          "gate": ("Implemented: fixed repair turn", (230, 243, 236), (30, 107, 69)),
          "sim": ("Model wording simulated", (255, 241, 224), (196, 106, 0)),
          "demo": ("Simulated overclaim (demo switch)", (255, 241, 224), (196, 106, 0))}
FOOT = ("Screens captured from the running prototype. Blue: implemented. Green: fixed repair turn, no model call. "
        "Orange: language-model wording comes from mock_model.py.")
W = 760  # frame width in the board

def board(name, title, frames, cols=2):
    tiles = []
    for i, (actor, caption, file, status) in enumerate(frames, 1):
        im = Image.open(os.path.join(F, file)).convert("RGB")
        im = im.resize((W, int(im.height * W / im.width)), Image.LANCZOS)
        head = 64
        t = Image.new("RGB", (W + 2, im.height + head + 2), "white")
        d = ImageDraw.Draw(t)
        d.rectangle([0, 0, W + 1, im.height + head + 1], outline=(200, 206, 213), width=2)
        d.rounded_rectangle([12, 14, 52, 50], 8, fill=COL[actor]); d.text((32, 32), str(i), font=font(22, True), fill="white", anchor="mm")
        d.text((64, 18), actor.upper(), font=font(15, True), fill=COL[actor])
        d.text((64, 38), caption, font=font(17), fill=(23, 32, 43))
        label, bg, fg = STATUS[status]
        tw = d.textlength(label, font=font(13, True))
        d.rounded_rectangle([W - tw - 30, 12, W - 10, 36], 6, fill=bg, outline=fg, width=2)
        d.text((W - tw - 20, 24), label, font=font(13, True), fill=fg, anchor="lm")
        t.paste(im, (1, head + 1)); tiles.append(t)
    gap = 24; rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    width = cols * (W + 2) + (cols + 1) * gap; top = 70
    heights = [max(t.height for t in r) for r in rows]
    foot = 36
    B = Image.new("RGB", (width, top + sum(heights) + gap * (len(rows) + 1) + foot), (245, 246, 248))
    d = ImageDraw.Draw(B); d.text((gap, 22), title, font=font(26, True), fill=(23, 32, 43))
    y = top
    for r, h in zip(rows, heights):
        x = gap
        for t in r:
            B.paste(t, (x, y)); x += W + 2 + gap
        y += h + gap
    d.text((gap, y + 4), FOOT, font=font(15), fill=(70, 80, 92))
    B.save(os.path.join(OUT, name)); print(name, B.size)

board("storyboard1_checked_answer.png", "Storyboard 1 · A checked answer the student can verify", [
    ("Student", "Asks with P(A) and P(B); scope shown first", "f1_1_ask.png", "impl"),
    ("System", "Cue, interpretation, cited sentences, calculation", "f1_2_answer.png", "sim"),
    ("Student", "Clicks '§2.3 source' on sentence 3", "f1_3_source.png", "impl"),
    ("System", "Passage highlighted: words that matched", "f1_3b_passage.png", "impl"),
    ("System", "Proposes revision slot; arguments shown", "f1_4_confirm.png", "impl"),
    ("Student", "Confirms; result read from the tool", "f1_5_done.png", "impl")])
board("storyboard2_clarify_correct.png", "Storyboard 2 · An ambiguous question is clarified, not guessed", [
    ("Student", "Asks: 'Are they independent? I don't have the numbers.'", "f2_0_ask.png", "impl"),
    ("System", "Unclear 'they': asks, offers three options", "f2_1_clarify.png", "gate"),
    ("Student", "Chooses to enter values; corrects details", "f2_2_correct.png", "impl"),
    ("System", "Checks the corrected values", "f2_3_checked.png", "sim")])
board("storyboard3_failure_recovery.png",
      "Storyboard 3 · Unsupported claims are caught and reported; a new out-of-scope question is declined", [
    ("Student", "Ticks the demo switch, then asks", "f3_0_ask.png", "impl"),
    ("System", "Demo overclaim: two sentences removed", "f3_1_removed.png", "demo"),
    ("Student", "Reports sentence 3; system rechecks", "f3_2_report.png", "impl"),
    ("System", "New question 'What is a Markov chain?': declined", "f3_3_decline.png", "gate")])
