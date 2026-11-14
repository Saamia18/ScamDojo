import sys; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
B = "http://localhost:8765/"
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 480, 900)
    pg.goto(B + "#/scan", wait_until="domcontentloaded"); pg.wait_for_selector(".phone")
    pg.fill("textarea.msg", "Dear user your KYC is expired. Pay Rs 5,000 to ramesh.k@okicici or call 9876543210. Update: http://sbi-kyc.top/login within 2 hours")
    pg.click("text=Check this message"); pg.wait_for_selector(".stamp")
    pg.click("button:has-text('evidence packet')"); pg.wait_for_selector("text=Evidence packet for 1930")
    pg.fill("input[placeholder='e.g. 5000']", "5000"); pg.check("label:has-text('I lost money') input"); pg.check("label:has-text('I shared an OTP') input")
    pg.click("button:has-text('Create packet')"); pg.wait_for_selector("text=Your evidence packet")
    print("category:", pg.inner_text(".note >> nth=0")[:90]); print("chips:", pg.locator(".overlay .chip").all_inner_texts())
    brief = pg.input_value("textarea[aria-label='Complaint brief']"); print("brief has phone/upi/utr-free:", "+91 9876543210" in brief, "ramesh.k@okicici" in brief, "Rs 5000" in brief)
    with pg.expect_download() as dl: pg.click("button:has-text('Download report')")
    path = dl.value.path(); html = open(path, encoding="utf-8").read(); print("download ok:", "<h1>Cyber fraud" in html, len(html), "bytes")
    pg.screenshot(path="shots/evidence.png")
    # Protect page button
    pg.goto(B + "#/protect"); pg.wait_for_selector("text=Complaint summary"); pg.click("button:has-text('Generate 1930 evidence packet')"); pg.wait_for_selector("text=Evidence packet for 1930"); print("protect modal opens")
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e])
    b.close()
