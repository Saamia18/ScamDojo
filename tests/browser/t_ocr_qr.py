import sys, io; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
from PIL import Image, ImageDraw
B = "http://localhost:8765/"
img = Image.new("RGB", (400, 300), "white"); d = ImageDraw.Draw(img); d.text((20, 20), "WhatsApp screenshot", fill="black"); img.save("/tmp/shot_test.png")
TESS_STUB = "window.Tesseract={createWorker:async(langs,n,opts)=>{window.__langs=langs;return{recognize:async()=>{opts.logger({status:'recognizing text',progress:0.5});return{data:{text:'Dear user your KYC is expired.\\nUpdate at http: //sbi - kyc . top / login\\nor your account will be blo-\\ncked today'}}},terminate:async()=>{}}}};"
JSQR_STUB = "window.jsQR=function(d,w,h,o){return {data:window.__qr||'upi://pay?pa=9876543210@ybl&pn=Cashback%20Desk&am=2000&tn=refund'}};"
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 480, 900)
    pg.route("**/tesseract.min.js", lambda r: r.fulfill(content_type="application/javascript", body=TESS_STUB))
    pg.route("**/jsQR.js", lambda r: r.fulfill(content_type="application/javascript", body=JSQR_STUB))
    posted = []
    pg.on("request", lambda rq: posted.append((rq.method, rq.url, rq.post_data)) if "/api/scan" in rq.url else None)
    pg.goto(B + "#/scan", wait_until="domcontentloaded"); pg.wait_for_selector(".drop")
    # 1) QR image: payment QR found -> intent chips -> choose RECEIVE
    pg.set_input_files(".drop input[type=file]", "/tmp/shot_test.png")
    pg.wait_for_selector(".stamp", timeout=8000); print("QR only:", pg.inner_text(".stamp"), "|", pg.inner_text(".intent .small").strip()[:60])
    pg.click("button.chip:has-text('RECEIVE')"); pg.wait_for_timeout(800)
    print("after intent=receive:", pg.inner_text(".stamp"), "| qr card:", pg.inner_text("h3:has-text('UPI payment QR')")[:50])
    pg.screenshot(path="shots/qr_scan.png", full_page=True)
    last = [x for x in posted if x[2]][-1]; print("sent:", last[2][:140])
    # 2) screenshot (no QR) -> OCR
    pg.evaluate("window.jsQR = () => null")
    pg.route("**/jsQR.js", lambda r: r.fulfill(content_type="application/javascript", body="window.jsQR=function(){return null};"))
    pg.goto(B + "#/scan"); pg.wait_for_selector(".drop")
    pg.evaluate("window.jsQR=()=>null")
    pg.set_input_files(".drop input[type=file]", "/tmp/shot_test.png")
    pg.wait_for_selector(".stamp", timeout=8000); pg.wait_for_timeout(500)
    print("OCR:", pg.inner_text(".stamp"), "| ocr note shown:", pg.locator("text=OCR can make mistakes").count() > 0, "| textarea/bubble:", pg.inner_text(".phone .bubble")[:60].replace("\n", " "))
    print("hi langs requested:", end=" ")
    pg.screenshot(path="shots/ocr_scan.png", full_page=True)
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e])
    b.close()
