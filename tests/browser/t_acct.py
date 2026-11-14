import sys, json; import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import browser_page
from playwright.sync_api import sync_playwright
B = "http://localhost:8765/"
def xp(pg): return pg.evaluate("JSON.parse(localStorage.getItem('scamdojo.v1')||'{}').xp||0")
with sync_playwright() as p:
    b, pg, errs = browser_page(p, 480, 900)
    # 1. guest earns XP via the daily card
    pg.goto(B + "#/daily", wait_until="domcontentloaded"); pg.wait_for_selector(".swipe"); pg.click("button.btn.scam"); pg.wait_for_selector(".reveal")
    guest_xp = xp(pg); print("guest xp:", guest_xp, "| nav:", pg.inner_text("a.pill[href='#/account']"))
    # 2. create account
    pg.goto(B + "#/account"); pg.wait_for_selector("form")
    pg.click("button.pill:has-text('Create account')")
    pg.fill("input[name=username]", "Meera_K"); pg.fill("input[name=display]", "Meera")
    pg.fill("input[name=new-password]", "tulsi garden 42"); pg.fill("input[name=confirm]", "tulsi garden 42")
    pg.screenshot(path="shots/acct_create.png")
    pg.click("button[type=submit]"); pg.wait_for_selector("#rc-ok")
    code = pg.inner_text(".display"); print("recovery code shown:", code)
    pg.screenshot(path="shots/acct_code.png")
    print("continue disabled until ticked:", pg.is_disabled("button:has-text('Continue')"))
    pg.check("#rc-ok"); pg.click("button:has-text('Continue')"); pg.wait_for_selector("text=Hi, Meera")
    pg.wait_for_timeout(1800)
    print("sync chip:", pg.inner_text(".chip >> nth=0"), "| nav:", pg.inner_text("a.pill[href='#/account']"))
    me = pg.evaluate("fetch('/api/me').then(r=>r.json())"); print("server has xp:", me["progress"]["xp"], "== local", guest_xp)
    pg.screenshot(path="shots/acct_profile.png")
    # 3. protect checkup score saved to the account
    pg.goto(B + "#/protect"); pg.wait_for_selector(".reason")
    for i in range(8): pg.locator(".reason").nth(i).locator("button").nth(0).click()
    pg.wait_for_timeout(2000)
    me = pg.evaluate("fetch('/api/me').then(r=>r.json())"); print("checkups on server:", me["progress"]["checkups"])
    # 4. log out wipes the device; log in restores
    pg.goto(B + "#/account"); pg.wait_for_selector("text=Hi, Meera"); pg.click("button:has-text('Log out')"); pg.wait_for_selector("text=Create account")
    print("after logout local xp:", xp(pg), "| nav:", pg.inner_text("a.pill[href='#/account']"))
    pg.fill("input[name=username]", "meera_k"); pg.fill("input[name=password]", "wrong password!"); pg.click("button[type=submit]"); pg.wait_for_selector("[role=alert]:not(.hide)")
    print("wrong pw message:", pg.inner_text("[role=alert]"))
    pg.fill("input[name=password]", "tulsi garden 42"); pg.click("button[type=submit]"); pg.wait_for_selector("text=Hi, Meera"); pg.wait_for_timeout(500)
    print("after login local xp:", xp(pg), "(restored from server)")
    # 5. reload keeps the session
    pg.reload(); pg.wait_for_selector("a.pill[href='#/account']"); pg.wait_for_timeout(600)
    print("after reload nav:", pg.inner_text("a.pill[href='#/account']"))
    # 6. Hindi account page
    pg.click("button.pill:has-text('हि')"); pg.wait_for_timeout(300); print("hindi:", pg.inner_text("h1"))
    pg.click("button.pill:has-text('EN')")
    # 7. change password, then log out and reset with the recovery code
    pg.goto(B + "#/account"); pg.wait_for_selector("text=Hi, Meera")
    pg.click("summary:has-text('Change password')")
    pg.fill("input[name=current]", "tulsi garden 42"); pg.fill("form:has(input[name=current]) input[name=new]", "river bank 2026"); pg.click("button:has-text('Save new password')"); pg.wait_for_timeout(600)
    pg.click("button:has-text('Log out')"); pg.wait_for_selector("text=Create account")
    pg.click("button:has-text('Forgot your password?')"); pg.wait_for_selector("input[name=recovery]")
    pg.fill("input[name=username]", "meera_k"); pg.fill("input[name=recovery]", code.lower()); pg.fill("input[name=new-password]", "lotus pond 2027"); pg.click("button[type=submit]")
    pg.wait_for_selector("#rc-ok"); new_code = pg.inner_text(".display"); print("reset ok, new code differs:", new_code != code, "|", pg.inner_text("h2 >> nth=0")[:40])
    pg.check("#rc-ok"); pg.click("button:has-text('Continue')"); pg.wait_for_selector("input[name=username]")
    pg.fill("input[name=username]", "meera_k"); pg.fill("input[name=password]", "lotus pond 2027"); pg.click("button[type=submit]"); pg.wait_for_selector("text=Hi, Meera")
    # 8. delete the account
    pg.click("summary:has-text('Delete account')"); pg.fill("input[name=delete]", "lotus pond 2027"); pg.click("button:has-text('Delete my account')"); pg.wait_for_selector("text=Create account")
    pg.fill("input[name=username]", "meera_k"); pg.fill("input[name=password]", "lotus pond 2027"); pg.click("button[type=submit]"); pg.wait_for_selector("[role=alert]:not(.hide)")
    print("login after delete:", pg.inner_text("[role=alert]"))
    print("REAL ERRORS:", [e for e in errs if "ERR_FAILED" not in e])
    b.close()
