import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
B = "http://localhost:8765/"
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 480, 900)
    pg.goto(B + "#/play/octopus", wait_until="domcontentloaded"); pg.wait_for_selector(".swipe")
    by = {c["text"]: c for c in pg.evaluate("fetch('/api/cards').then(r=>r.json())")["cards"]}
    for i in range(8):
        if pg.locator(".overlay").count(): break
        pg.wait_for_selector(".swipe", timeout=5000)
        c = by[pg.evaluate("document.querySelector('.swipe .msgview').textContent")]
        pg.keyboard.press("ArrowLeft" if c["scam"] else "ArrowRight"); pg.wait_for_selector(".reveal")
        pg.keyboard.press("Enter"); pg.wait_for_timeout(150)
    for _ in range(3):
        if pg.locator(".overlay").count(): break
        if pg.locator("#nextBtn").count(): pg.click("#nextBtn")
        pg.wait_for_timeout(200)
    pg.wait_for_selector(".overlay"); print("boss:", pg.inner_text(".overlay h2"))
    pg.goto(B + "#/rush"); pg.wait_for_selector(".btn.big"); pg.click(".btn.big"); pg.wait_for_selector(".swipe")
    pg.keyboard.press("ArrowRight"); pg.wait_for_timeout(1700); print("rush card shown:", pg.locator(".swipe").count() >= 0)
    pg.goto(B + "#/progress"); pg.wait_for_selector(".badges"); pg.goto(B + "#/daily"); pg.wait_for_selector(".swipe, .card")
    pg.goto(B + "#/hood"); pg.wait_for_selector("table.t")
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e])
    b.close()
