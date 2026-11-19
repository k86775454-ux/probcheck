"""Capture focused frames of each interaction for the storyboards.

    python scripts/frames.py docs/frames      (with the app running on port 8765)
Set CHROME to your Chrome binary if it is not /usr/bin/google-chrome (the frames were made on Linux;
on macOS: CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")."""
import os
import sys
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; URL = "http://localhost:8765/"
def box(page, sel, last=False):
    loc = page.locator(sel); loc = loc.last if last else loc.first
    return loc.evaluate("e => {const r = e.getBoundingClientRect(); "
                        "return {x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height};}")
def clip(page, name, top_sel, bottom_sel=None, pad=10):
    page.wait_for_timeout(900)          # let smooth scrolling finish before measuring
    t = box(page, top_sel); b = box(page, bottom_sel or top_sel, last=True)
    x = min(t["x"], b["x"]) - pad; y = t["y"] - pad
    w = max(t["x"] + t["width"], b["x"] + b["width"]) - x + pad; h = b["y"] + b["height"] - y + pad
    page.screenshot(path=f"{OUT}/{name}.png", clip={"x": x, "y": y, "width": w, "height": h}, full_page=True)
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=os.environ.get("CHROME", "/usr/bin/google-chrome"), args=["--no-sandbox"])
    page = br.new_page(viewport={"width": 1300, "height": 1000}, device_scale_factor=2)
    page.goto(URL)
    # S1
    page.fill("#msg", "Can two events be mutually exclusive and independent? Let P(A)=0.4 and P(B)=0.5.")
    page.click("#send"); page.wait_for_selector(".cue.checked")
    clip(page, "f1_1_ask", ".scope", "#transcript")          # the transcript shows the full question
    clip(page, "f1_2_answer", ".cue", ".steps")
    page.locator("ol.answer li").nth(2).locator("button.src").click()
    clip(page, "f1_3_source", "ol.answer li:nth-child(3)", pad=34)
    clip(page, "f1_3b_passage", ".passage.hl")
    page.click("text=Add a revision slot for this topic"); page.wait_for_selector("#toolbox button.primary")
    clip(page, "f1_4_confirm", "#toolbox")
    page.click("#toolbox button.primary"); page.wait_for_selector("#toolbox >> text=Added")
    clip(page, "f1_5_done", "#toolbox")
    # S2
    page.goto(URL)                                             # fresh transcript for each storyboard
    page.click("text=Ambiguous question"); page.wait_for_selector(".cue.clarify")
    clip(page, "f2_0_ask", ".row", "#transcript")
    clip(page, "f2_1_clarify", ".cue", "#card .chips")
    page.click("text=I have P(A), P(B) and P(A∩B): test independence")
    ins = page.locator(".form input"); ins.nth(0).fill("0.3"); ins.nth(1).fill("0.5"); ins.nth(2).fill("0.2")
    page.locator(".form select").select_option("independence")
    clip(page, "f2_2_correct", ".understood")
    page.click("text=Check again"); page.wait_for_selector(".cue.checked")
    clip(page, "f2_3_checked", ".cue", ".steps")
    # S3
    page.goto(URL)
    page.check("#overclaim"); page.fill("#msg", "Can two events be mutually exclusive and independent? Let P(A)=0.4 and P(B)=0.5.")
    page.click("#send"); page.wait_for_selector("details.removed")
    clip(page, "f3_0_ask", ".row", "#transcript")
    page.click("details.removed summary")
    clip(page, "f3_1_removed", "ol.answer", "details.removed")
    page.locator("ol.answer li").nth(2).locator("text=This source doesn't support it").click(); page.wait_for_selector(".reportbox")
    clip(page, "f3_2_report", "ol.answer li:nth-child(3)", pad=34)
    page.uncheck("#overclaim"); page.click("text=Outside the notes"); page.wait_for_selector(".cue.cannot_check")
    clip(page, "f3_3_decline", ".cue", ".reply")
    br.close()
