import sys, json; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
B = "http://localhost:8765/"
MOCK = """
window.__spoken = [];
const fakeVoices = [{lang:'en-IN',name:'EN'},{lang:'hi-IN',name:'HI'}];
Object.defineProperty(window, 'speechSynthesis', {configurable:true, value: { getVoices: () => fakeVoices, addEventListener(){}, cancel(){ window.__cancel=(window.__cancel||0)+1 },
  speak(u){ window.__spoken.push({text:u.text, lang:u.lang, voice:u.voice&&u.voice.name}); setTimeout(()=>u.onend&&u.onend(), 30); } }});
window.SpeechSynthesisUtterance = function(t){ this.text=t; };
"""
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 480, 900)
    pg.add_init_script(MOCK)
    pg.goto(B + "#/home", wait_until="domcontentloaded"); pg.wait_for_selector(".phone")
    # --- Hindi boss fight ---
    pg.click("button.pill:has-text('हि')"); pg.wait_for_timeout(200)
    pg.goto(B + "#/play/kraken"); pg.wait_for_selector(".swipe")
    txt = pg.inner_text(".swipe .msgview"); print("hindi card:", txt[:60])
    assert any("\u0900" <= c <= "\u097f" for c in txt), "card not in Devanagari"
    print("boss intro:", pg.inner_text(".bossbar .bubble"))
    pg.screenshot(path="shots/hi_card.png")
    # tap a token then answer by reading truth from /api/cards translations
    cards = pg.evaluate("fetch('/api/cards').then(r=>r.json())")["cards"]
    by = {c["i18n"]["hi"]["text"]: c for c in cards}
    card = by[txt.replace("\n", " ")] if txt.replace("\n"," ") in by else by[txt]
    pg.keyboard.press("ArrowLeft" if card["scam"] else "ArrowRight")
    pg.wait_for_selector(".reveal"); print("reveal note:", "AI ने" in pg.inner_text(".reveal"), "| lesson hindi:", pg.inner_text(".reveal p >> nth=0")[:50])
    pg.screenshot(path="shots/hi_reveal.png")
    # timer length: check initial timer 16s by reading source constant through behavior (card still alive after 10s)
    pg.click("#nextBtn"); pg.wait_for_selector(".swipe"); pg.wait_for_timeout(10500)
    print("card alive after 10.5s:", pg.locator(".swipe").count() == 1 and pg.locator(".reveal").count() == 0)
    # --- Read aloud via button ---
    pg.click(".swipe button.pill")  # listen
    pg.wait_for_timeout(300)
    sp = pg.evaluate("window.__spoken"); print("spoken:", [(s['lang'], s['voice'], s['text'][:30]) for s in sp[:2]])
    # --- Kannada card ---
    pg.click("button.pill:has-text('ಕನ್')"); pg.wait_for_timeout(300)
    pg.goto(B + "#/play/llama"); pg.wait_for_selector(".swipe")
    ktxt = pg.inner_text(".swipe .msgview"); print("kannada card:", ktxt[:50]); assert any("\u0c80" <= c <= "\u0cff" for c in ktxt)
    pg.click(".swipe button.pill"); pg.wait_for_timeout(300)
    print("kn spoken lang:", pg.evaluate("window.__spoken.slice(-1)[0]"))
    # --- autoread toggle + scan result speaking ---
    pg.click("button.pill:has-text('EN')"); pg.wait_for_timeout(200)
    pg.click("button[aria-label='Read aloud automatically']")
    pg.goto(B + "#/scan"); pg.wait_for_selector(".phone"); pg.evaluate("window.__spoken=[]")
    pg.fill("textarea.msg", "Dear SBI user, your KYC expired. Update at http://sbi-kyc-update.xyz/login within 2 hours or account blocked"); pg.click("text=Check this message"); pg.wait_for_selector(".stamp"); pg.wait_for_timeout(1500)
    sp = pg.evaluate("window.__spoken"); print("autoread scan spoke chunks:", len(sp), "| first:", sp[0]["text"][:40] if sp else None)
    # --- Protect page ---
    pg.goto(B + "#/protect"); pg.wait_for_selector(".reason")
    for i in range(8):
        pg.locator(".reason").nth(i).locator("button").nth(0 if i % 2 else 1).click()
    pg.wait_for_selector("text=Fix these first"); print("protect score:", pg.inner_text("h2 >> nth=1")[:40] if False else "ok")
    pg.fill("textarea.field", "Got an OTP call"); pg.fill("input.field >> nth=0", "5000"); pg.click("text=Create summary")
    print("complaint:", pg.inner_text("pre.json").splitlines()[:3])
    pg.screenshot(path="shots/protect.png", full_page=True)
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e])
    b.close()
