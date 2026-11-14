import sys, csv, json; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from shot import browser_page
from playwright.sync_api import sync_playwright
import os; os.environ["SCAMDOJO_FEEDS"] = "0"
from engine import fusion
B = "http://localhost:8765/"
def rows(f): return list(csv.DictReader(open("engine/data/" + f, encoding="utf-8")))
sets = {"dev": rows("india_testset.csv"), "blind": rows("india_blindset.csv"), "cards": rows("cards_eval.csv")}
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 480, 900)
    ctx = pg.context
    pg.goto(B, wait_until="domcontentloaded"); pg.wait_for_selector(".phone")
    pg.evaluate("navigator.serviceWorker.ready.then(()=>1)"); pg.wait_for_timeout(1500)
    keys = pg.evaluate("caches.keys().then(async ks => { const out = {}; for (const k of ks) { const c = await caches.open(k); out[k] = (await c.keys()).map(r => new URL(r.url).pathname).length } return out })")
    print("caches:", keys)
    print("cards cached:", pg.evaluate("caches.match('/api/cards').then(r => !!r)"), "| sw controlled after reload:", end=" ")
    pg.reload(); pg.wait_for_selector(".phone"); print(pg.evaluate("!!navigator.serviceWorker.controller"))
    man = pg.evaluate("fetch('/manifest.json').then(r=>r.json())"); print("manifest:", man["name"], man["display"], [i["sizes"] for i in man["icons"]])
    # ---- go offline ----
    ctx.set_offline(True)
    pg.reload(); pg.wait_for_selector(".phone", timeout=8000); print("offline reload ok, title:", pg.title()[:30])
    pg.goto(B + "#/play/kraken"); pg.wait_for_selector(".swipe", timeout=8000); pg.keyboard.press("ArrowLeft"); pg.wait_for_selector(".reveal", timeout=5000); print("offline Boss Rush card played")
    pg.goto(B + "#/scan"); pg.wait_for_selector(".phone")
    pg.fill("textarea.msg", "Dear SBI user, your KYC is expired. Update immediately at http://sbi-kyc-update.xyz/login or your account will be blocked today")
    pg.click("text=Check this message"); pg.wait_for_selector(".stamp", timeout=8000)
    print("offline scan:", pg.inner_text(".stamp"), "| banner:", pg.locator("text=Offline quick check").count() > 0, "| confidence:", pg.inner_text(".verdict .small.muted"))
    pg.click("button:has-text('✏️')"); pg.fill("textarea.msg", "845120 is your OTP for HDFC NetBanking login. Valid 5 mins. Do not share it with anyone, HDFC never asks.")
    pg.click("text=Check this message"); pg.wait_for_timeout(800); print("offline genuine OTP:", pg.inner_text(".stamp"))
    pg.screenshot(path="shots/offline_scan.png", full_page=True)
    # ---- how good is the offline port? ----
    for name, data in sets.items():
        texts = [r["text"] for r in data]
        res = pg.evaluate("async (texts) => { const m = await import('/js/offline.js'); const out = []; for (const t of texts) { const r = await m.offlineScan({text: t}); out.push(r.risk) } return out }", texts)
        tp = fp = tn = fn = agree = 0; maxdiff = 0
        for r, js_risk in zip(data, res):
            a = fusion.analyze(r["text"]); py = fusion.combine(0.0, a["components"]["rules"], a["components"]["links"], a["components"]["upi"])
            y = int(r["label"]); pred = js_risk >= 0.5
            tp += pred and y; fp += pred and not y; tn += (not pred) and not y; fn += (not pred) and y
            agree += (js_risk >= 0.5) == (py >= 0.5)
        P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn) if tp + fn else 0; F = 2 * P * R / (P + R) if P + R else 0
        print("offline %-5s n=%-3d P=%.2f R=%.2f F1=%.2f | agrees with python-no-model on %d/%d" % (name, len(data), P, R, F, agree, len(data)))
    ctx.set_offline(False)
    pg.goto(B + "#/home"); pg.goto(B + "#/scan"); pg.wait_for_selector(".phone"); pg.fill("textarea.msg", "Your KYC is expired http://sbi-kyc.xyz/login within 2 hours"); pg.click("text=Check this message"); pg.wait_for_selector(".stamp"); pg.wait_for_timeout(500)
    print("back online -> offline banner gone:", pg.locator("text=Offline quick check").count() == 0, "| confidence:", pg.inner_text(".verdict .small.muted"))
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e and "net::ERR" not in e])
    b.close()
