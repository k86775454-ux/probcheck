import os, sys
from playwright.sync_api import sync_playwright
OUT = sys.argv[1]; URL = "http://localhost:8765/"
def shot(page, name, full=False):
    page.wait_for_timeout(400); page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=os.environ.get("CHROME", "/usr/bin/google-chrome"), args=["--no-sandbox"])
    page = b.new_page(viewport={"width": 1400, "height": 1000}, device_scale_factor=1.5)
    page.on("console", lambda m: print("console:", m.text))
    page.on("pageerror", lambda e: print("pageerror:", e))
    page.goto(URL); shot(page, "00_start")
    # Storyboard 1: checked answer, view source, revision slot
    page.click("text=Mutually exclusive and independent? (with numbers)"); page.wait_for_selector(".cue.checked")
    shot(page, "s1_a_checked", full=True)
    page.locator("ol.answer li").nth(2).locator("button.src").click(); shot(page, "s1_b_source", full=True)
    page.click("text=Add a revision slot for this topic"); page.wait_for_selector("#toolbox button.primary"); shot(page, "s1_c_confirm", full=True)
    page.click("#toolbox button.primary"); page.wait_for_selector("text=to your local schedule"); shot(page, "s1_d_done", full=True)
    # Storyboard 2: ambiguous -> clarify -> correct values
    page.click("text=Ambiguous question"); page.wait_for_selector(".cue.clarify"); shot(page, "s2_a_clarify", full=True)
    page.click("text=I have P(A), P(B) and P(A∩B): test independence")
    f = page.locator(".form"); ins = f.locator("input")
    ins.nth(0).fill("0.3"); ins.nth(1).fill("0.5"); ins.nth(2).fill("0.2"); shot(page, "s2_b_form", full=True)
    page.click("text=Check again"); page.wait_for_selector(".cue.checked"); shot(page, "s2_c_checked", full=True)
    # Storyboard 3: overconfident model reply removed; report
    page.check("#overclaim"); page.click("text=Mutually exclusive and independent? (with numbers)"); page.wait_for_selector("details.removed")
    page.click("details.removed summary"); shot(page, "s3_a_removed", full=True)
    page.locator("ol.answer li").nth(1).locator("text=This source doesn't support it").click(); page.wait_for_selector(".reportbox")
    shot(page, "s3_b_report", full=True)
    page.uncheck("#overclaim")
    page.click("text=Outside the notes"); page.wait_for_selector(".cue.cannot_check"); shot(page, "s3_c_decline", full=True)
    b.close()
