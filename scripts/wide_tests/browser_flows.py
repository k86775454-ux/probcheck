"""Wide test 6: every flow of the page in headless Chrome (Playwright), with no browser errors.

    python app.py --port 8766 &        # from a scratch copy, as for http_requests.py
    python scripts/wide_tests/browser_flows.py http://localhost:8766/

Examples and source links, the form round trip, invalid values, the clarify options, the overclaim
demo and a report, the revision slot, and further questions. CHROME= sets the browser path."""
import os, re, sys
from playwright.sync_api import sync_playwright

URL = sys.argv[1]
FAIL, ERRORS = [], []


def expect(cond, what):
    if not cond:
        FAIL.append(what)


with sync_playwright() as p:
    br = p.chromium.launch(executable_path=os.environ.get("CHROME", "/usr/bin/google-chrome"), args=["--no-sandbox"])
    pg = br.new_page(viewport={"width": 1280, "height": 900})
    pg.on("pageerror", lambda e: ERRORS.append("pageerror: %s" % e))
    pg.on("console", lambda m: ERRORS.append("console %s: %s" % (m.type, m.text)) if m.type in ("error", "warning") else None)
    pg.goto(URL)

    def ask(q):
        pg.fill("#msg", q)
        pg.press("#msg", "Enter")
        pg.wait_for_function("document.querySelector('#card .cue') !== null || document.querySelector('#card .alert') !== null")
        return pg.inner_text("#card")

    def cue():
        return pg.get_attribute("#card .cue", "class").split()[-1]

    # 1. every example button
    for b in pg.query_selector_all("#examples button"):
        pg.evaluate("document.getElementById('card').replaceChildren()")
        b.click()
        pg.wait_for_selector("#card .cue")
        expect(pg.query_selector("#card .understood") is not None, "example %s: no interpretation box" % b.inner_text())
        for i, src in enumerate(pg.query_selector_all("#card ol.answer li .src")):
            src.click()
            hl = pg.query_selector("#card .passage.hl")
            expect(hl is not None, "example %s: source %d does not highlight a passage" % (b.inner_text(), i))
            expect(hl is not None and hl.query_selector("mark") is not None, "example %s: source %d highlights no words" % (b.inner_text(), i))

    # 2. exact fractions survive the form round trip
    t = ask("P(A)=1/3, P(B)=1/2, P(A∩B)=1/6. Are A and B independent?")
    expect(cue() == "checked" and "P(A) ≈ 0.333333" in t, "fractions: chips or status wrong: " + t[:200])
    steps1 = pg.inner_text("#card .steps")
    pg.click("text=Correct these details")
    expect(pg.input_value("input[aria-label='P(A)']") != "", "form not prefilled")
    pg.click("text=Check again")
    pg.wait_for_function("document.querySelector('#card .understood strong').textContent.includes('corrected')")
    expect(cue() == "checked" and pg.inner_text("#card .steps") == steps1, "form round trip changed the answer")

    # 3. values the parser cannot use open the form at once
    ask("P(A)=0,3, P(B)=0.4. Are A and B independent?")
    expect(cue() == "invalid", "decimal comma not rejected")
    expect(pg.is_visible("#card .form"), "form not opened for invalid values")

    # 4. clarify, then each option
    ask("Are they independent?")
    expect(cue() == "clarify", "pronoun not clarified")
    pg.click("#card .chips button >> nth=1")
    expect(pg.is_visible("#card .form"), "enter values option did not open the form")
    pg.click("#card .chips button >> nth=0")
    pg.wait_for_function("document.querySelector('#card .cue') && !document.querySelector('#card .cue').classList.contains('clarify')")
    expect("Can mutually exclusive" in pg.inner_text("#card .understood"), "clarify choice not answered")

    # 5. the overclaim demo removes exactly two sentences, then a report on a good sentence keeps it
    pg.check("#overclaim")
    ask("P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?")
    summ = pg.inner_text("#card details.removed summary")
    expect(summ.startswith("I removed 2 sentences"), "overclaim demo: " + summ)
    pg.uncheck("#overclaim")
    n_before = len(pg.query_selector_all("#card ol.answer li"))
    pg.click("#card ol.answer li >> nth=0 >> text=This source doesn't support it")
    pg.wait_for_selector("#card .reportbox")
    box = pg.inner_text("#card .reportbox")
    expect("saved" in box, "report not saved: " + box)
    expect(len(pg.query_selector_all("#card ol.answer li")) == n_before or "removed it" in box, "report changed the list unexpectedly")

    # 6. revision slot: confirm, then cancel
    ask("P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?")
    pg.click("text=Add a revision slot for this topic")
    pg.wait_for_selector("#toolbox button.primary")
    pg.click("#toolbox button.primary")
    pg.wait_for_function("/Added|already in your schedule|Not added/.test(document.getElementById('toolbox').innerText)")
    expect(re.search("Added|already in your schedule", pg.inner_text("#toolbox")), "slot not added: " + pg.inner_text("#toolbox"))
    ask("P(A)=0.3, P(B)=0.5, P(A∩B)=0.15. Are A and B independent?")
    pg.click("text=Add a revision slot for this topic")
    pg.wait_for_selector("#toolbox button.primary")
    pg.click("#toolbox >> text=Cancel")
    pg.wait_for_function("document.getElementById('toolbox').innerText.includes('Cancelled')")

    # 7. more questions through the page
    cases = [("What is a Markov chain?", "cannot_check", None),
             ("P(A)=1e-8, P(B)=0.5. A and B are independent. What is P(A∩B)?", "checked", "P(A) = 1e-8"),
             ("Pr(A)=30%, Pr(B)=40 percent, Pr(A∩B)=0.12. Independent?", "checked", "P(A) = 0.3"),
             ("P(A)=0.3, P(A)=0.4. What is P(A∪B)?", "invalid", "more than once"),
             ("P(B|A)=0.5, P(A)=0.4. What is P(A∩B)?", "cannot_check", "not covered"),
             ("P(A)=0.3. What is P(A|B) if A and B are independent?", "checked", "provided P(B) > 0"),
             ("P(A)=1, P(B)=0.4. Are A and B independent?", "checked", "independent"),
             ("P(A)=1/3, P(B)=1/2, P(A∩B)=0.1667. Are A and B independent?", "checked", "differ only after rounding")]
    for q, status, text in cases:
        t = ask(q)
        expect(cue() == status, "%s: status %s, expected %s" % (q, cue(), status))
        if text:
            expect(text in t, "%s: page does not show %r" % (q, text))
    # a stated "not independent" stays in the form: resubmitting keeps the rejection, unticking drops it
    t = ask("A and B are not independent. P(A)=0.3, P(B)=0.4, P(A∩B)=0.12. What is P(A∪B)?")
    expect(cue() == "invalid" and pg.is_visible("#card #not_independent"), "negated premise not shown in the form")
    pg.click("text=Check again")
    pg.wait_for_function("document.querySelector('#card .understood strong').textContent.includes('corrected')")
    expect(cue() == "invalid", "resubmitting the form dropped the stated 'not independent'")
    pg.uncheck("#card #not_independent")
    pg.click("text=Check again")
    pg.wait_for_function("document.querySelector('#card .cue.checked') !== null")
    expect("0.58" in pg.inner_text("#card"), "unticking the premise did not give P(A∪B) = 0.58")
    # empty input does nothing
    before = pg.inner_text("#transcript")
    pg.fill("#msg", "   ")
    pg.press("#msg", "Enter")
    expect(pg.inner_text("#transcript") == before, "empty question was sent")
    br.close()

print("failures:", len(FAIL), "browser errors:", len(ERRORS))
for f in FAIL + ERRORS:
    print("  ", f)
