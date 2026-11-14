import sys
from playwright.sync_api import sync_playwright

def browser_page(p, w=1180, h=900):
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": w, "height": h})
    pg.route("**/*", lambda r: r.abort() if ("googleapis" in r.request.url or "gstatic" in r.request.url) else r.continue_())
    errs = []
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
    return b, pg, errs
