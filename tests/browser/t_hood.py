import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 1000, 900)
    pg.goto("http://localhost:8765/#/hood", wait_until="domcontentloaded"); pg.wait_for_selector("table.t"); pg.wait_for_timeout(500)
    pg.screenshot(path="shots/hood_full.png", full_page=True)
    for k in ("Dev set", "Unseen templates", "Game cards"): pg.click("button.pill:has-text('%s')" % k); pg.wait_for_timeout(150)
    print("sections:", [e.inner_text() for e in pg.locator("h2").all()])
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e])
    b.close()
