// ==========================================================================
// ScamDojo Autopilot Mode — Hands-Free 60-Second Guided Hackathon Simulation
// ==========================================================================
import { play } from './sound.js';

let isRunning = false;
let isPaused = false;
let currentStep = 0;
let abortSignal = { aborted: false };
let skipResolve = null;

let cursorEl = null;
let hudEl = null;
let dialogEl = null;
let finaleEl = null;

// ---------- Helper: Sleep / Timing / Pause / Skip ----------
function sleep(ms) {
  return new Promise((resolve) => {
    let elapsed = 0;
    const interval = 50;

    const check = () => {
      if (abortSignal.aborted) {
        resolve();
        return;
      }
      if (skipResolve) {
        const doSkip = skipResolve;
        skipResolve = null;
        doSkip();
        resolve();
        return;
      }
      if (!isPaused) {
        elapsed += interval;
      }
      if (elapsed >= ms) {
        resolve();
      } else {
        setTimeout(check, interval);
      }
    };
    setTimeout(check, interval);
  });
}

function waitFor(selectorOrFn, timeout = 5000) {
  return new Promise((resolve) => {
    const start = performance.now();
    const check = () => {
      if (abortSignal.aborted) return resolve(null);
      const res = typeof selectorOrFn === 'function' ? selectorOrFn() : document.querySelector(selectorOrFn);
      if (res) return resolve(res);
      if (performance.now() - start > timeout) return resolve(null);
      setTimeout(check, 60);
    };
    check();
  });
}

// ---------- 1. Virtual Arcade Cursor ----------
function createCursor() {
  if (cursorEl) cursorEl.remove();
  cursorEl = document.createElement('div');
  cursorEl.id = 'sim-cursor';
  cursorEl.innerHTML = `
    <svg viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M2 2L11.5 25.5L16 16L25.5 11.5L2 2Z" fill="#FFB400" stroke="#1B1F4B" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M5.5 5.5L11.5 20.5L14.8 13.8L21.5 10.5L5.5 5.5Z" fill="#D6247F"/>
    </svg>
  `;
  document.body.appendChild(cursorEl);
  // Initial position offscreen or near center top
  cursorEl.style.transform = `translate3d(${window.innerWidth * 0.5}px, 60px, 0)`;
  return cursorEl;
}

function getCenter(el) {
  const rect = el.getBoundingClientRect();
  return {
    x: rect.left + rect.width * 0.5,
    y: rect.top + rect.height * 0.5,
  };
}

async function moveCursorTo(target, offset = { x: 0.5, y: 0.5 }, duration = 450) {
  if (abortSignal.aborted || !cursorEl) return;
  let el = typeof target === 'string' ? await waitFor(target) : target;
  if (!el) return;

  // Scroll into view if outside viewport bounds
  const rect = el.getBoundingClientRect();
  if (rect.top < 80 || rect.bottom > window.innerHeight - 80) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await sleep(250);
  }

  const updatedRect = el.getBoundingClientRect();
  const x = Math.round(updatedRect.left + updatedRect.width * offset.x);
  const y = Math.round(updatedRect.top + updatedRect.height * offset.y);

  cursorEl.style.transform = `translate3d(${x}px, ${y}px, 0)`;
  await sleep(duration);
}

function triggerRipple(x, y) {
  const ripple = document.createElement('div');
  ripple.className = 'sim-ripple';
  ripple.style.left = `${x}px`;
  ripple.style.top = `${y}px`;
  document.body.appendChild(ripple);
  setTimeout(() => ripple.remove(), 600);
}

async function clickElement(target, offset = { x: 0.5, y: 0.5 }) {
  if (abortSignal.aborted) return;
  const el = typeof target === 'string' ? await waitFor(target) : target;
  if (!el) return;

  await moveCursorTo(el, offset, 400);
  if (abortSignal.aborted) return;

  const rect = el.getBoundingClientRect();
  const x = rect.left + rect.width * offset.x;
  const y = rect.top + rect.height * offset.y;

  cursorEl.classList.add('sim-clicking');
  triggerRipple(x, y);
  play('tap');

  // Trigger click
  if (typeof el.click === 'function') {
    el.click();
  } else {
    el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
  }

  await sleep(180);
  cursorEl.classList.remove('sim-clicking');
}

async function typeInto(textareaOrInput, text, speed = 18) {
  if (abortSignal.aborted) return;
  const el = typeof textareaOrInput === 'string' ? await waitFor(textareaOrInput) : textareaOrInput;
  if (!el) return;

  await moveCursorTo(el, { x: 0.2, y: 0.3 }, 350);
  el.focus();
  el.value = '';
  el.dispatchEvent(new Event('input', { bubbles: true }));

  for (let i = 0; i < text.length; i++) {
    if (abortSignal.aborted) return;
    el.value += text[i];
    el.dispatchEvent(new Event('input', { bubbles: true }));
    if (i % 6 === 0) play('tap');
    await sleep(speed);
  }
  await sleep(200);
}

// ---------- 2. Floating HUD Controller ----------
function createHUD() {
  if (hudEl) hudEl.remove();
  hudEl = document.createElement('div');
  hudEl.id = 'sim-hud';
  hudEl.innerHTML = `
    <div class="sim-hud-badge">
      <span class="sim-dot"></span>
      <span id="sim-step-text">AUTOPILOT: STEP 1 / 6</span>
    </div>
    <button class="sim-hud-btn" id="sim-btn-pause" type="button" title="Pause / Resume">⏸️ Pause</button>
    <button class="sim-hud-btn" id="sim-btn-skip" type="button" title="Skip to next step">⏭️ Skip</button>
    <button class="sim-hud-btn sim-hud-exit" id="sim-btn-exit" type="button" title="Exit Simulation (Esc)">✕ Exit</button>
  `;
  document.body.appendChild(hudEl);

  hudEl.querySelector('#sim-btn-pause').addEventListener('click', togglePause);
  hudEl.querySelector('#sim-btn-skip').addEventListener('click', skipCurrentStep);
  hudEl.querySelector('#sim-btn-exit').addEventListener('click', stopSimulation);
}

function updateHUDStep(step) {
  currentStep = step;
  const txt = document.getElementById('sim-step-text');
  if (txt) txt.textContent = `AUTOPILOT: STEP ${step} / 6`;
}

function togglePause() {
  isPaused = !isPaused;
  const btn = document.getElementById('sim-btn-pause');
  if (btn) {
    btn.innerHTML = isPaused ? '▶️ Resume' : '⏸️ Pause';
    btn.style.background = isPaused ? '#FFB400' : '';
    btn.style.color = isPaused ? '#1B1F4B' : '';
  }
}

function skipCurrentStep() {
  if (skipResolve) {
    const doSkip = skipResolve;
    skipResolve = null;
    doSkip();
  }
}

// ---------- 3. Explainer Dialogue Card ----------
function createDialog() {
  if (dialogEl) dialogEl.remove();
  dialogEl = document.createElement('div');
  dialogEl.id = 'sim-dialog';
  dialogEl.innerHTML = `
    <div class="sim-dialog-header">
      <h3 class="sim-dialog-title" id="sim-dialog-title">⚡ STEP 1: FORENSIC AI SCANNER</h3>
    </div>
    <div class="sim-dialog-progress-track">
      <div class="sim-dialog-progress-fill" id="sim-dialog-progress" style="width: 16%;"></div>
    </div>
    <p class="sim-dialog-body" id="sim-dialog-body">Initializing simulation...</p>
    <div class="sim-dialog-badge" id="sim-dialog-badge">⚡ 0.6ms Latency • Pure-Python</div>
  `;
  document.body.appendChild(dialogEl);
}

function showDialogue(title, body, badgeText, stepNumber = currentStep) {
  if (!dialogEl) createDialog();
  const t = document.getElementById('sim-dialog-title');
  const b = document.getElementById('sim-dialog-body');
  const g = document.getElementById('sim-dialog-badge');
  const p = document.getElementById('sim-dialog-progress');

  if (t) t.innerHTML = title;
  if (b) b.innerHTML = body;
  if (g) g.innerHTML = badgeText;
  if (p) p.style.width = `${Math.round((stepNumber / 6) * 100)}%`;

  dialogEl.style.animation = 'none';
  // Trigger reflow
  void dialogEl.offsetWidth;
  dialogEl.style.animation = 'sim-dialog-pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards';
}

// ---------- 4. Celebration Finale Banner ----------
function showFinale() {
  if (finaleEl) finaleEl.remove();
  finaleEl = document.createElement('div');
  finaleEl.id = 'sim-finale';
  finaleEl.innerHTML = `
    <div class="sim-finale-icon">🏆</div>
    <h2 class="sim-finale-title">SIMULATION COMPLETE!</h2>
    <p class="sim-finale-sub">You've seen ScamDojo's 0.6ms forensic scanner, on-device OCR privacy, gamified combat, and 1930 incident reports.</p>
    <div class="row" style="justify-content: center; gap: 12px;">
      <button class="btn big" id="sim-btn-done" type="button" style="background:#FFB400;color:#1B1F4B;font-weight:800;">🎮 Try It Yourself</button>
    </div>
  `;
  document.body.appendChild(finaleEl);
  play('win');

  finaleEl.querySelector('#sim-btn-done').addEventListener('click', stopSimulation);
}

// ---------- 5. Global Escape Handler ----------
function onKeyDown(e) {
  if (e.key === 'Escape' && isRunning) {
    stopSimulation();
  }
}

// ==========================================================================
// 6-ACT SIMULATION CHOREOGRAPHY
// ==========================================================================

export async function startSimulation() {
  if (isRunning) return;
  isRunning = true;
  isPaused = false;
  currentStep = 1;
  abortSignal = { aborted: false };

  window.addEventListener('keydown', onKeyDown);

  // Setup DOM elements
  createCursor();
  createHUD();
  createDialog();

  try {
    // ----------------------------------------------------
    // ACT 1: Forensic AI Scanner
    // ----------------------------------------------------
    updateHUDStep(1);
    showDialogue(
      '⚡ STEP 1: FORENSIC AI SCANNER',
      'Navigating to the Scanner. Simulating a targeted Indian banking phishing SMS with urgent KYC threats and a malicious lookalike domain.',
      '⚡ 0.6ms Latency • Pure-Python TF-IDF + Rules',
      1
    );

    location.hash = '#/scan';
    await sleep(650);
    if (abortSignal.aborted) return;

    // Type scam message
    const msgArea = await waitFor('textarea.msg');
    if (msgArea) {
      const sampleText = 'Dear SBI user, your YONO account is restricted. Complete KYC today: http://yono-sbi-care.top/kyc or your account will be blocked within 2 hours.';
      await typeInto(msgArea, sampleText, 14);
    }
    if (abortSignal.aborted) return;

    // Click "Scan message"
    const scanBtn = await waitFor('.screen ~ button.btn.big, .phone button.btn.big, button.btn.big');
    if (scanBtn) {
      await clickElement(scanBtn);
    }
    await sleep(900);
    if (abortSignal.aborted) return;

    // Point to verdict
    const gaugeEl = await waitFor('.gauge, .stamp.scam, .stamp');
    if (gaugeEl) {
      await moveCursorTo(gaugeEl, { x: 0.5, y: 0.5 }, 400);
    }
    showDialogue(
      '⚡ STEP 1: FORENSIC AI SCANNER',
      'Instant <b>98% SCAM Verdict</b>! Noisy-OR fusion flags lookalike SBI domain, urgent countdown deadline, and deceptive credential capture in 0.6ms.',
      '⚡ 0.6ms Latency • Pure-Python Model',
      1
    );
    await sleep(2800);
    if (abortSignal.aborted) return;

    // ----------------------------------------------------
    // ACT 2: Zero-Knowledge Privacy & OCR
    // ----------------------------------------------------
    updateHUDStep(2);
    showDialogue(
      '🔒 STEP 2: ZERO-KNOWLEDGE PRIVACY & OCR',
      'Navigating to the Protect Hub. ScamDojo uses 100% on-device processing. Screenshots are OCR-scanned locally via Tesseract.js—images are never uploaded.',
      '🔒 Zero-Knowledge • Client-Side Tesseract.js & QR',
      2
    );

    location.hash = '#/protect';
    await sleep(650);
    if (abortSignal.aborted) return;

    const checkupCard = await waitFor('.card');
    if (checkupCard) {
      await moveCursorTo(checkupCard, { x: 0.3, y: 0.2 }, 500);
    }
    await sleep(1500);
    if (abortSignal.aborted) return;

    // Scroll down to emergency steps
    const helplineBtn = await waitFor('a[href*="1930"], a[href*="cybercrime"]');
    if (helplineBtn) {
      await moveCursorTo(helplineBtn, { x: 0.5, y: 0.5 }, 500);
    }
    showDialogue(
      '🔒 STEP 2: ZERO-KNOWLEDGE PRIVACY & OCR',
      'Victim emergency checklist: call 1930 within the golden hour, freeze UPI accounts, and detect deceptive reverse-charge UPI payment QR traps.',
      '🛡️ 1930 Ready • Reverse UPI-QR Detection',
      2
    );
    await sleep(2600);
    if (abortSignal.aborted) return;

    // ----------------------------------------------------
    // ACT 3: Boss Rush — Combat vs OTP Octopus
    // ----------------------------------------------------
    updateHUDStep(3);
    showDialogue(
      '🐙 STEP 3: BOSS RUSH — OTP OCTOPUS',
      'Entering Boss Rush to battle the <b>OTP Octopus</b>! Defending a ₹10,000 virtual wallet against high-pressure verification scams.',
      '🎮 Gamified Defense • ₹10,000 Virtual Wallet',
      3
    );

    location.hash = '#/play/octopus';
    await sleep(750);
    if (abortSignal.aborted) return;

    // Wait for stage card to mount
    const stageCard = await waitFor('.stage .swipe, .stage');
    if (stageCard) {
      await moveCursorTo(stageCard, { x: 0.5, y: 0.3 }, 500);
    }
    await sleep(900);
    if (abortSignal.aborted) return;

    showDialogue(
      '🐙 STEP 3: BOSS RUSH — OTP OCTOPUS',
      'Active Learning: Tapping suspicious red-flag words in the message lands a <b>CRITICAL HIT</b> on the scammer boss!',
      '💥 Critical Hits (+200 XP) • Adaptive Difficulty',
      3
    );

    // Find and tap a red flag token
    const tokens = document.querySelectorAll('.msgview .tok');
    if (tokens && tokens.length > 0) {
      // Find a token mentioning OTP or suspicious words
      let targetTok = [...tokens].find((el) => /OTP|PIN|Share|49,999|pay|fee|verify/i.test(el.textContent)) || tokens[Math.min(3, tokens.length - 1)];
      if (targetTok) {
        await clickElement(targetTok);
      }
    }
    await sleep(600);
    if (abortSignal.aborted) return;

    // Click "Scam" button
    const scamSwipeBtn = await waitFor('button.btn.scam');
    if (scamSwipeBtn) {
      await clickElement(scamSwipeBtn);
    }
    play('crit');
    await sleep(2600);
    if (abortSignal.aborted) return;

    // ----------------------------------------------------
    // ACT 4: Live 1v1 Duels
    // ----------------------------------------------------
    updateHUDStep(4);
    showDialogue(
      '⚔️ STEP 4: REAL-TIME 1v1 DUELS',
      'Beat the AI & Live 1v1 Multiplayer. Race a friend to red flags in real-time over WebSockets with server-authoritative 20s rounds.',
      '⚔️ WebSocket Transport • 1v1 Room Matchmaking',
      4
    );

    location.hash = '#/duel';
    await sleep(650);
    if (abortSignal.aborted) return;

    const playFriendBtn = await waitFor('a[href="#/duel/live"]');
    if (playFriendBtn) {
      await clickElement(playFriendBtn);
      await sleep(600);
    }
    if (abortSignal.aborted) return;

    const codeField = await waitFor('input[maxlength="4"]');
    if (codeField) {
      await moveCursorTo(codeField, { x: 0.5, y: 0.5 }, 400);
    }
    showDialogue(
      '⚔️ STEP 4: REAL-TIME 1v1 DUELS',
      'Cross-device matchmaking: share 4-character room codes across phones or laptops. If an opponent does not join in 2 minutes, an AI bot steps in automatically.',
      '🤖 Smart AI Fallback • Authoritative Clock',
      4
    );
    await sleep(2800);
    if (abortSignal.aborted) return;

    // ----------------------------------------------------
    // ACT 5: Under the Hood Telemetry
    // ----------------------------------------------------
    updateHUDStep(5);
    showDialogue(
      '📊 STEP 5: MODEL TRANSPARENCY & METRICS',
      'Under the Hood dashboard: Complete transparency with confusion matrices, calibration curves, and single-threaded inference speeds (1,400 msg/sec).',
      '📊 Bootstrap 95% Confidence Intervals',
      5
    );

    location.hash = '#/hood';
    await sleep(750);
    if (abortSignal.aborted) return;

    const metricsTable = await waitFor('table, .metrics, .card');
    if (metricsTable) {
      await moveCursorTo(metricsTable, { x: 0.5, y: 0.3 }, 500);
    }
    await sleep(1500);
    if (abortSignal.aborted) return;

    showDialogue(
      '📊 STEP 5: MODEL TRANSPARENCY & METRICS',
      'Honest benchmarks: 55 unit tests passing, calibrated 50% threshold trade-offs, and ablation studies showing text, rules, and link contributions.',
      '⚡ 1,400 msg/sec • 55/55 Passing Unit Tests',
      5
    );
    await sleep(2800);
    if (abortSignal.aborted) return;

    // ----------------------------------------------------
    // ACT 6: 1930 Cybercrime Evidence Packet
    // ----------------------------------------------------
    updateHUDStep(6);
    showDialogue(
      '📄 STEP 6: 1930 EVIDENCE PACKET',
      'Generating an official, ready-to-file complaint packet for the 1930 National Cyber Crime Reporting Portal (cybercrime.gov.in).',
      '📄 SHA-256 Forensic Integrity • Automated IoC Extraction',
      6
    );

    location.hash = '#/scan';
    await sleep(650);
    if (abortSignal.aborted) return;

    // Click sample chip or run scan
    const sampleChip = await waitFor('.row .chip, button.chip');
    if (sampleChip) {
      await clickElement(sampleChip);
      await sleep(700);
    }
    if (abortSignal.aborted) return;

    // Scroll to and click the Evidence Packet button
    const evidenceBtn = await waitFor('button.btn.small.scam, button.btn.scam');
    if (evidenceBtn && /evidence|1930/i.test(evidenceBtn.textContent)) {
      await clickElement(evidenceBtn);
      await sleep(800);

      // Dialog is open, point to it
      const overlayBox = await waitFor('.overlay .card');
      if (overlayBox) {
        await moveCursorTo(overlayBox, { x: 0.5, y: 0.4 }, 500);
      }
      showDialogue(
        '📄 STEP 6: 1930 EVIDENCE PACKET',
        'Extracts phone numbers, suspicious links, and IFSC codes into a copy-ready brief with SHA-256 fingerprint and printable PDF report.',
        '📄 Stateless & Private • Zero Storage',
        6
      );
      await sleep(2800);
      if (abortSignal.aborted) return;

      // Close modal
      const cancelBtn = await waitFor('.overlay button.btn.ghost, .overlay button');
      if (cancelBtn) {
        await clickElement(cancelBtn);
      }
    }
    await sleep(600);
    if (abortSignal.aborted) return;

    // ----------------------------------------------------
    // FINALE: Celebration & Handover
    // ----------------------------------------------------
    if (dialogEl) dialogEl.remove();
    showFinale();
    await sleep(4000);
    if (abortSignal.aborted) return;

    stopSimulation();
  } catch (err) {
    console.error('Simulation error:', err);
    stopSimulation();
  }
}

export function stopSimulation() {
  abortSignal.aborted = true;
  isRunning = false;
  isPaused = false;
  currentStep = 0;

  window.removeEventListener('keydown', onKeyDown);

  if (cursorEl) {
    cursorEl.remove();
    cursorEl = null;
  }
  if (hudEl) {
    hudEl.remove();
    hudEl = null;
  }
  if (dialogEl) {
    dialogEl.remove();
    dialogEl = null;
  }
  if (finaleEl) {
    finaleEl.remove();
    finaleEl = null;
  }
  document.querySelectorAll('.sim-ripple').forEach((el) => el.remove());
}
