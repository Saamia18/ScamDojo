# Browser tests (optional)

These drive the real app in headless Chromium and check every feature end to end: games, accounts, OCR and QR scanning (with stubbed
Tesseract.js / jsQR so they run offline), evidence packets, live 1v1 duels in two browsers, the offline PWA, and the metrics page.

    pip install playwright && playwright install chromium
    tests/browser/with_server.sh tests/browser/t_live.py      # one script
    for t in t_regress t_new t_duel t_hood t_ocr_qr t_evidence t_acct t_live t_pwa; do tests/browser/with_server.sh tests/browser/$t.py; done

They print what they checked plus "REAL ERRORS: []" when the page raised no unexpected errors. (A few expected 401/503 console lines appear in
the account and offline tests: those are deliberate wrong-password and offline requests.) Screenshots go to ./shots.
On Windows run the same commands from Git Bash or WSL.
