import sys, time; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
B = "http://localhost:8765/"
with sync_playwright() as p:
    b, a, errs_a = browser_page(p, 480, 900)
    ctx2 = b.new_context(viewport={"width": 480, "height": 900}); c = ctx2.new_page(); c.add_init_script("(()=>{const O=window.WebSocket;window.__in=[];window.__out=[];window.WebSocket=function(u){const w=new O(u);w.addEventListener('message',e=>window.__in.push(e.data));const s=w.send.bind(w);w.send=d=>{window.__out.push(d);s(d)};return w};window.WebSocket.prototype=O.prototype;})();")
    c.route("**/*", lambda r: r.abort() if ("googleapis" in r.request.url or "gstatic" in r.request.url) else r.continue_())
    errs_c = []; c.on("pageerror", lambda e: errs_c.append(str(e)))
    # --- Player A creates a room ---
    a.goto(B + "#/duel/live", wait_until="domcontentloaded"); a.wait_for_selector("text=Create a room")
    a.fill("input[aria-label='Your name']", "Asha"); a.click("text=Create a room"); a.wait_for_selector("text=Waiting for a friend")
    code = a.inner_text(".display"); print("room code:", code)
    a.screenshot(path="shots/live_wait.png")
    # --- Player B joins from the invite link ---
    c.goto(B + "#/duel/live/" + code, wait_until="domcontentloaded"); c.wait_for_selector("input[aria-label='Room code']")
    c.fill("input[aria-label='Your name']", "Bala"); c.click("button:has-text('Join')")
    a.wait_for_selector("text=Get ready", timeout=8000); print("countdown shown on A")
    a.wait_for_selector(".bubble .tok", timeout=8000); c.wait_for_selector(".bubble .tok", timeout=8000)
    ta = a.inner_text(".bubble .msgview"); tc = c.inner_text(".bubble .msgview"); print("same message on both:", ta == tc)
    cards = {x["text"]: x for x in a.evaluate("fetch('/api/cards').then(r=>r.json())")["cards"]}
    done_rounds = 0
    for rnd in range(6):
        a.wait_for_selector(".bubble .tok", timeout=12000)
        text = a.inner_text(".bubble .msgview"); card = cards.get(text.replace("\n", " ")) or cards.get(text)
        real = [h for h in card["ai"]["highlights"] if h["kind"] in ("rule", "link")] if card and card["scam"] else []
        if real:
            words = card["text"].split(" "); pos = 0; idx = []
            for i, w in enumerate(words):
                s = card["text"].index(w, pos); pos = s + len(w)
                for k, h in enumerate(real):
                    if s < h["end"] and h["start"] < pos: idx.append((k, i))
            a.locator(".bubble .tok").nth(idx[0][1]).click(); a.wait_for_selector("text=You found", timeout=4000)
            if len(real) > 1:   # more flags left: B races for the same one and is too late, then both finish
                c.wait_for_timeout(400); c.locator(".bubble .tok").nth(idx[0][1]).click(); c.wait_for_selector("text=Too late", timeout=4000)
                if rnd == 0: a.screenshot(path="shots/live_round.png"); c.screenshot(path="shots/live_round_b.png")
                a.click("text=Done"); c.click("text=Done")
        else:
            a.click("text=Looks clean"); c.click("text=Looks clean")
        a.wait_for_selector(".reveal", timeout=6000); done_rounds += 1
        if rnd == 0: a.screenshot(path="shots/live_recap.png")
        if a.locator(".overlay").count(): break
        # wait for the next round or the end
        try: a.wait_for_function("document.querySelector('.reveal') === null || !!document.querySelector('.overlay')", timeout=9000)
        except Exception: break
        if a.locator(".overlay").count(): break
    a.wait_for_selector(".overlay", timeout=15000); print("A result:", a.inner_text(".overlay h2"), "|", a.inner_text(".overlay .display"))
    c.wait_for_selector(".overlay", timeout=5000); print("B result:", c.inner_text(".overlay h2"))
    print("rounds played:", done_rounds)
    # --- bot fallback: a lone player ---
    a.goto(B + "#/home"); a.goto(B + "#/duel/live"); a.wait_for_selector("text=Create a room"); a.click("text=Create a room"); a.wait_for_selector("text=Waiting for a friend")
    t0 = time.time(); a.wait_for_selector("text=Get ready", timeout=25000); print("AI joined after %.1fs" % (time.time() - t0))
    print("REAL ERRORS A:", [e for e in errs_a if "ERR_FAILED" not in e], "C:", errs_c)
    b.close()
