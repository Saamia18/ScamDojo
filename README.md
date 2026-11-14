# ScamDojo 🥋

**An AI scam detector for Indian messages, QR codes and screenshots, with games that train you to spot fraud.**
INNOVEX 2026 · PS 05 AI-Powered Cybersecurity (fraud detection, phishing prevention, digital security)

Paste a message, drop a WhatsApp screenshot, or scan a UPI QR code → get a risk score, the exact words and links that gave it away, and what to do next, including a ready-to-file **1930 / cybercrime.gov.in evidence packet**. Then play against the same engine: five scammer bosses, a red-flag race against the AI or a live friend, and an endless inbox rush. Works offline as an installable app.

## Run it

```bash
pip install -r requirements.txt     # Flask, gunicorn (not needed on Windows), flask-sock
python server.py                    # http://localhost:8000  (Flask development server; live duels use a built-in WebSocket on port 8001)
```

Production (Render, Railway, any Linux host): `gunicorn server:app -c gunicorn.conf.py` (this is what the `Procfile` runs; one worker with 32 threads on purpose, because rate limits, duel rooms and caches live in memory). On Windows use `python server.py`.

```bash
python -m unittest discover -s tests -v     # 55 automated tests
python -m engine.train                      # retrain + regenerate every metric on the "Under the hood" page
python scripts/build_cards.py               # rebuild the game cards
python scripts/build_offline.py             # re-export the offline rules pack from the Python definitions
python scripts/make_icons.py                # redraw the app icons
tests/browser/with_server.sh tests/browser/t_live.py   # optional end-to-end browser tests (see tests/browser/README.md)
```

Environment variables (all optional): `PORT`, `SCAMDOJO_DB` (SQLite path), `SCAMDOJO_SECURE=1`, `SCAMDOJO_TRUST_PROXY=1` (behind Render/nginx), `SCAMDOJO_RATE_LIMIT`, `ANTHROPIC_API_KEY` + `SCAMDOJO_LLM_MODEL` + `SCAMDOJO_LLM_DAILY_CAP` (LLM card generator), `SCAMDOJO_FEEDS=0` (disable live threat feeds), `GSB_API_KEY` (Google Safe Browsing), `SCAMDOJO_RDAP=1` (domain-age lookups), `SCAMDOJO_INTEL_BUDGET_MS`.

## Upgrade status (v0.2), against the upgrade specification

| # | Item | Status | How it was verified |
|---|---|---|---|
| 1 | **Production server** | Done with **Flask + gunicorn** (the spec allowed Flask; FastAPI/uvicorn could not be installed or tested in the build sandbox). All previous endpoints kept, CORS only on public endpoints, per-client rate limiting, JSON errors with no stack traces, `ProxyFix` behind a proxy. | 55 unit tests on the Flask test client; real load test: 1,000 concurrent scans from 25 threads in 1.8 s (about 540 req/s, no errors, p95 82 ms) on Flask's threaded server. gunicorn itself was not run in the sandbox. |
| 2 | **Screenshot OCR + UPI QR scanning** | Done. Image drop zone, paste, file picker and camera; QR via the native `BarcodeDetector` or **jsQR**; OCR via **Tesseract.js**; all in the browser, images are never uploaded. `POST /api/scan` takes text, `source` (text/ocr/qr), `intent` (receive/pay/unknown) and QR payloads. New `engine/upi.py`: a payment QR when you expect to **receive** money scores 0.95. | Engine and UPI logic unit-tested; browser flow tested end to end with **stubbed** Tesseract.js and jsQR (the real libraries load from a CDN and could not be downloaded in the sandbox, so test them once on a real device). |
| 3 | **Persistent state + profiles** | Done on SQLite (`db.py`): `users`, `sessions`, `progress`, `scan_history`, `leaderboard`, `generated_cards`. `store.js` is a write-through cache (instant from `localStorage`, debounced sync to `GET/PUT/POST /api/progress`). **Privacy changes to the spec:** scan history stores the verdict and scam type only, never the message, and both history and the leaderboard are opt-in. The leaderboard is client-reported, so XP growth is capped per hour and it is for fun. | Unit tests (opt-in, no message text stored, cascade delete); browser account test. |
| 4 | **Live 1v1 duels (WebSockets)** | Done. `/ws/duel/<code>`: 4-character room codes, invite links, server-authoritative rounds (first valid tap claims a red flag), live score and timer, **AI opponent joins after 15 s** or if a human leaves. Production transport is **flask-sock on the same port**; `ws_transport.py` is a small built-in WebSocket server used by `python server.py` for development. Live duels use the English cards so both players see the same text. | 11 room-logic tests; a **full 6-round match in two real browsers** plus the 15 s AI fallback, over the built-in transport. The flask-sock route (about 10 lines) was not executed because flask-sock cannot be installed in the sandbox: try two browser tabs once after deploying. |
| 5 | **Adversarial card generator** | Done. `POST /api/cards/generate` (login, 6/hour per user, daily cap) uses an **LLM** (Anthropic Messages API) when `ANTHROPIC_API_KEY` is set, otherwise a **template mutator**. Every card is validated (schema, masked phone numbers, no working official domains in scam cards, translated flags must exist in the text, the engine must find a red flag, markup rejected), cached in the database and mixed into the decks (served a bit more often, tagged "AI-generated"). | Validation, LLM path (mocked transport) and fallback unit-tested. **No real LLM call was made** (no key or network in the sandbox). |
| 6 | **Live threat intelligence** | Done, fail-soft. OpenPhish feed (refreshed every 6 h), optional Google Safe Browsing, optional RDAP domain age, short-link expansion (known shorteners only, never fetches the redirect target), 150 ms time budget with TTL caches. Look-alike checks extended (more Indian banks and UPI apps; e.g. `hdfc-kyc-update.in` is caught). | Unit-tested with simulated feeds, including chains, official targets, an SSRF check and a deliberately slow lookup. **No live feed was contacted.** |
| 7 | **1930 evidence packet** | Done in **`engine/evidence.py`** (the existing `engine/report.py` is the evaluation module, so it was kept separate). Extracts phone numbers, UPI IDs and links, e-mails, amounts, dates/times, IFSC codes and long numbers; suggests a portal-style category; plain-text brief to copy, printable HTML report (print to PDF), SHA-256 fingerprint, tailored next steps. Button on the scan result and on Protect. Stateless: nothing stored. | Unit tests (including an XSS attempt in the notes field); browser test of the form, copy and download. |
| 8 | **PWA / offline** | Done. `manifest.json`, icons, `sw.js` (stale-while-revalidate, version injected by the server so releases refresh the cache), and an **offline quick check** (`js/offline.js`): the same rules, link and UPI logic exported from Python, but no AI text model and no feeds, always shown as low confidence. | Browser test: install, go offline, reload, play Boss Rush, scan. The offline port agrees with the Python engine (run without its text model) on 137/137, 58/60 and 54/55 messages. **Offline F1: 0.92 dev, 0.75 blind, 0.89 game cards** (online: 1.00, 0.86, 0.96). |

## How the engine works (the part that is scored)

```
message → normalise → ┬ text model (TF-IDF + logistic regression, pure Python)
                      ├ 25 India-specific scam rules (English / Hinglish / a little Hindi)
                      └ link analyzer (look-alike domains, shorteners, IP hosts, free hosting, .apk)
                        → fusion (noisy-OR) → verdict + confidence + highlighted evidence
```

* **Normalisation** undoes zero-width characters, look-alike letters (Cyrillic `а`), leetspeak (`b4nk`) and spaced-out words (`K Y C`), while keeping a map back to the original characters so highlights land on exactly what the user pasted.
* **Text model** is trained by `engine/train.py` with no ML libraries. Every word has a learned weight, so the page can show which words moved the score.
* **Rules** return a plain-language reason and tip for each match. Warnings like "never share your OTP" are not flagged; "as requested, your card is blocked" is not a threat.
* **Link analyzer** knows 38 Indian brands and their official domains. `sbi-kyc-update.xyz`, `paytrn.com` and `hdfcbank.com.verify-now.top` are caught; `sbi.co.in` and `*.gov.in` are not.
* **Fusion**: `risk = 1 − (1 − 0.85·text)(1 − rules)(1 − 0.95·links)`; verdict ≥ 65% scam, < 35% safe, otherwise "be careful". Confidence comes from distance to the line and agreement between the three parts. Low confidence is shown to the user, not hidden.
* **API**: `POST /api/scan` (and `/api/analyze`). Mean engine latency 0.6 ms per message. Pasted message text is never stored or logged.

## Measured results (generated by `engine/train.py`, nothing typed by hand)

| Set | Messages | What it is | Fused P / R / F1 | Text-only F1 |
|---|---|---|---|---|
| Unseen templates | 240 | training-style templates the model never saw | 1.00 / 1.00 / 1.00 | 1.00 |
| Dev set | 137 | hand-written, **used while tuning** the rules | 1.00 / 1.00 / 1.00 | 0.96 |
| **Blind set** | 60 | hand-written **after** the engine was frozen, never tuned on | **0.80 / 0.93 / 0.86** (95% interval for F1: 0.75 to 0.94) | 0.88 |
| Game cards | 55 | the messages in the game | 0.94 / 0.97 / 0.96 | 0.96 |

**Please read these honestly.** The seed training data is template-based, so the first two rows are upper bounds. The blind set is the real signal, and on it the fused engine is *not* better than the text model alone: the rules produce false alarms on genuine messages that contain scary words ("Never click links asking you to update KYC", a cab OTP, "you won the hackathon"). The "Under the hood" page lists every miss. All sets are small and written by us, so none of this is a claim about real-world accuracy.

### The technical report on the Under the hood page (all computed by `python -m engine.train`)

* **Uncertainty:** 95% bootstrap intervals for precision, recall and F1 on every set. With 60 blind messages the F1 could plausibly be anywhere from 0.75 to 0.94.
* **Threshold trade-off:** precision/recall at every alert threshold, with a precision-recall chart. We use 50%.
* **Calibration:** on the blind set, messages the engine scored 80–100% were scams 92% of the time, but the 40–80% band is close to a coin flip, which is why that band is shown as "be careful".
* **Confidence reliability:** the "high / medium / low" label is meaningful: on the blind set the verdict was right for 100% of high-confidence messages (41), 60% of medium (10) and 44% of low (9).
* **Per message-type results:** shows the weak spots (for example cab OTPs and friendly chat that mention "blocked" or "won").
* **Per-rule precision:** which of the 25 rules fire on genuine messages, so false alarms can be fixed rule by rule.
* **Evasion test:** 136 scams disguised six ways (hidden characters, look-alike letters, spaced-out words, leetspeak, mixed, alternating case), with the normaliser on and off. Honest result: undisguised recall is 97.8%; without the normaliser the disguises cost 2 to 6 points, with it most of that is restored. It is a modest, self-designed test.
* **Phishing-link benchmark (link analyzer alone):** 45 phishing and 49 genuine links (23 of them from sites not in our brand list). At a 50% threshold: precision 1.00, recall 0.89 (40 of 45), no false alarms. The 5 misses (unknown-brand look-alike, one shortener, three generic bait links) are listed on the page.
* **Speed:** median 0.5 ms, 95th percentile about 3 ms, roughly 1,400 messages per second on one Python thread.
* **Threat model** (16 attack types marked covered / partial / not covered) and a **security and privacy design** list, including known weaknesses.

## Accounts (optional)

Create an account, log in, and your progress follows you to any device. Guests keep playing without one; guest progress is merged into the account on signup or login, and wiped from the device on logout.

* **What is stored:** username, display name, scrypt password hash, recovery-code hash, and a small progress record (XP, badges, streak, bosses beaten, weak-spot stats, language, security-checkup scores). **Pasted messages, emails and phone numbers are never stored.**
* **No email:** password reset uses a one-time recovery code shown at signup (stored hashed, replaced after use). If a user loses both the password and the code, the account cannot be recovered.
* **Security:** scrypt with a random salt per user; sessions are random 256-bit tokens in HttpOnly, SameSite=Lax cookies (add `Secure` automatically behind HTTPS, or set `SCAMDOJO_SECURE=1`) with only a hash stored; 5 failed logins per username per 10 minutes then lockout; identical error text and a dummy hash for unknown usernames; JSON-only and same-origin checks on state-changing requests; account endpoints send no CORS headers; progress is whitelisted and size-capped; changing the password signs out every device.
* **User control:** download my data (JSON), change password, delete account (removes the account, sessions and saved progress).
* **Known weaknesses:** no email verification, no two-factor login, lockout counters live in memory, plain HTTP unless the host provides TLS, and SQLite on a temporary disk is wiped on redeploy (free Render tier) unless you attach a persistent disk and point `SCAMDOJO_DB` at it. XP merging across devices keeps the higher value, so spending XP on a hint on one device can be undone by another device.

## What is included

**Engine:** normaliser, text model + training script, 25 rules, link analyzer (38 brands), fusion with confidence, JSON API, automated tests, evaluation with ablation, confusion matrices, failure cases and latency.

**Web app (no build step):**
* **Home / Scan:** phone-style scanner with live highlights, risk gauge, reasons with evidence, link autopsy, score breakdown, influential words, next steps with 1930 and cybercrime.gov.in.
* **Boss Rush:** 5 bosses (KYC Kraken, Lottery Llama, OTP Octopus, Job Offer Jackal, Courier Cobra), ₹10,000 wallet, swipe or buttons or ← →, tap the red flags for critical hits, Hint and Slow-time power-ups, per-card timer, boss taunts.
* **Beat the AI (red-flag race):** you and the engine hunt the same message at once. The AI claims its findings one by one on a timer; tap suspicious parts before it does (+2), tap harmless words (−1), or press "Looks clean" on genuine messages. Not a swipe game.
* **Inbox Rush:** endless, timer shrinks as you score, high score.
* **Scam of the day:** one card per day, keeps your streak.
* **Adaptive difficulty:** scam types you miss are served more often (weak spots on the Progress page).
* **Progress:** XP and levels, day streak, 11 badges, weak-spot chart, shareable result image (canvas).
* **Under the hood:** pipeline, measured metrics, failures, top words, live API box.
* **Dojo Bot:** small rule-based helper (no LLM) that answers common questions and checks pasted messages.
* **Protect:** a personal security checkup (8 questions, tips for each "no"), an "I have been scammed" step-by-step guide (bank, 1930, cybercrime.gov.in), and a complaint-summary builder you can read out to 1930 or paste into the complaint form.
* **Read aloud:** a 🔊 button on every message, result, lesson and Protect section, plus an automatic mode (🗣️ in the top bar). It uses the browser's built-in speech engine, so nothing is sent anywhere. In automatic mode the game timer waits while a message is being read.
* **Languages:** the interface, all 55 game cards, their lessons, the boss text and the Protect page are in English, Hindi and Kannada. Red flags in translated cards are hand-picked phrases; the AI verdict is computed on the English original (the game says so).
* Longer timers: 16 s per card in Boss Rush, 12 s down to 5 s in Inbox Rush, 20 s per round in Beat the AI.
* Sound effects. Login is optional; guests keep progress in the browser.

## What is NOT done yet (be upfront with the judges)

1. **Real training data.** Only a template-based seed set plus our hand-written test sets. Add the UCI SMS Spam Collection and any phishing-URL dataset (check licences) as `engine/data/extra_train.csv` (columns `text,label`) and retrain. Do this first: it is the biggest accuracy win.
2. **Fix the false alarms** listed on the Under the hood page (rules firing on warnings and friendly chat), then write a *new* blind set. Don't tune on the current one.
3. **OCR and QR** use libraries loaded from a CDN; test them once on a real phone. Hindi and Kannada OCR needs the matching Tesseract language data, which downloads on first use.
4. **LLM plain-language rewriting of explanations** is not built (the LLM is used only to generate game cards). Reasons are fixed templates. An LLM should only reword the explanation, never decide the verdict.
5. **Translations need a native-speaker review** (Hindi and Kannada were drafted quickly). The engine's reasons and tips, badge names and the Under the hood page are still English only. The engine itself understands English and Hinglish well but Hindi/Kannada script only a little, so pasted Hindi or Kannada messages are checked less reliably.
5b. **Read aloud** depends on the voices installed on the device. Hindi and Kannada voices are often missing on Windows (Settings > Time & language > Speech > add voices); the app tells the user when a voice is missing. Reasons and tips are read in English.
6. **A community scam map** is not built. Accounts have no email verification, no two-factor login and no admin tools.
7. **Browser testing** was done in headless Chromium only (desktop and a phone-sized viewport). Test on real phones, especially swipe gestures, the camera QR scanner, speech, and the share image. Also test once, after deploying: two browser tabs in a live duel (the production WebSocket route uses flask-sock), the real OCR/QR libraries, and an LLM key if you set one.
8. **Audio lessons** (recorded, not synthesised) are not built. There is also no browser extension or WhatsApp bot yet.
9. Google Fonts load from the internet; offline the page uses cached fonts if it has seen them, otherwise system fonts.

## Deploy

The Procfile runs gunicorn; `render.yaml` sets the proxy/secure-cookie variables. Add `ANTHROPIC_API_KEY` (cards), `GSB_API_KEY` (Safe Browsing) and `SCAMDOJO_RDAP=1` if you want those extras.

* **Render / Railway:** `render.yaml` and `Procfile` are included (start command `gunicorn server:app -c gunicorn.conf.py`, build command `pip install -r requirements.txt`).
* **Render's free tier sleeps** after inactivity and has a temporary disk (accounts and generated cards are wiped on redeploy): open the site a minute before judging, or ping `/api/health`. For durable data attach a persistent disk and set `SCAMDOJO_DB`.
* **HTTPS matters:** the service worker (offline mode) and camera scanning need HTTPS, except on localhost. Render provides it.
* Vercel serves static files well but this project needs the Python server for `/api/*` and WebSockets.

## Project layout

```
server.py                 Flask app: static files, JSON API, service-worker injection, WebSocket route
db.py  accounts.py        SQLite schema; users, sessions, progress (scrypt, validation)
history.py                opt-in scan history (metadata only) and leaderboard
duel.py  ws_transport.py  live 1v1 duel rooms; built-in WebSocket server for development
llm.py                    validated card generator (LLM + template fallback)
engine/                   normalize, textclf, rules, urlcheck, brands, upi, entities, ocr, intel, evidence, fusion, report, train
engine/data/              seed generator, dev/blind/link/card evaluation sets
engine/model/             model.json (weights) and metrics.json (every number on the metrics page)
web/                      index.html, manifest.json, sw.js, css, icons, js (ES modules, no build), data (cards, offline pack)
scripts/                  build_cards, build_offline, make_icons, card translations
tests/                    55 unit tests (engine, accounts, duels, threat intel, card generator, server)
tests/browser/            optional end-to-end browser tests (Playwright)
```

## Safety notes

ScamDojo is a screening and learning tool, not legal advice. Emergency guidance is fixed text (call 1930, report at cybercrime.gov.in). The game's wallet is virtual. Scam messages in the game are fictional and use made-up numbers and look-alike domains.
