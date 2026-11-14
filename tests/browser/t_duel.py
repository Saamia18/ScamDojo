import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
B = "http://localhost:8765/"
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 480, 900)
    pg.goto(B + "#/duel", wait_until="domcontentloaded"); pg.wait_for_selector(".btn.big"); pg.click(".btn.big")
    cards = pg.evaluate("fetch('/api/cards').then(r=>r.json())")["cards"]
    by = {c["text"]: c for c in cards}
    for rnd in range(8):
        pg.wait_for_selector(".swipe .tok", timeout=5000)
        txt = pg.evaluate("document.querySelector('.swipe .msgview').textContent")
        c = by[txt]
        real = [h for h in c["ai"]["highlights"] if h["kind"] in ("rule", "link")]
        if c["scam"] and real:
            # tap the first token of the first real flag span
            first = real[0]; words = txt.split(" ")
            pos = 0; idx = 0
            for i, w in enumerate(words):
                s = txt.index(w, pos); pos = s + len(w)
                if s < first["end"] and first["start"] < pos: idx = i; break
            pg.locator(".swipe .tok").nth(idx).click()
            if rnd == 2: pg.wait_for_timeout(2600); pg.screenshot(path="shots/duel_mid.png")
            if pg.locator("text=Done").count(): pg.click("text=Done")
        else:
            pg.click("text=Looks clean")
        pg.wait_for_selector("#nextBtn"); 
        if rnd == 2: pg.screenshot(path="shots/duel_reveal.png")
        pg.click("#nextBtn"); pg.wait_for_timeout(100)
    pg.wait_for_selector(".overlay"); print(pg.inner_text(".overlay h2"), "|", pg.inner_text(".overlay .display"))
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e])
    b.close()
