// Read aloud, using the browser's built-in speech engine (Web Speech API). Nothing is sent to any server.
// Hindi and Kannada voices depend on what the device has installed; we say so when one is missing.
import { store, save } from './store.js';
import { t } from './i18n.js';

const LANG = { en: 'en-IN', hi: 'hi-IN', kn: 'kn-IN' };
export const supported = typeof window !== 'undefined' && 'speechSynthesis' in window;
let voices = [], token = 0;
if (supported) {
  const load = () => { voices = speechSynthesis.getVoices(); };
  load();
  speechSynthesis.addEventListener('voiceschanged', load);
}

function notice(msg) {
  const el = document.createElement('div');
  el.className = 'toast'; el.setAttribute('role', 'status'); el.textContent = msg;
  document.body.append(el);
  setTimeout(() => el.remove(), 4200);
}

export function voiceFor(lang) {
  const code = (LANG[lang] || lang).toLowerCase();
  return voices.find((v) => v.lang.toLowerCase().replace('_', '-') === code) || voices.find((v) => v.lang.toLowerCase().startsWith(code.slice(0, 2))) || null;
}

// Long utterances get cut off in some browsers, so speak sentence by sentence.
function chunks(text) {
  const out = [];
  for (const s of String(text).split(/(?<=[.!?।])\s+/)) {
    let rest = s.trim();
    while (rest.length > 180) {
      const cut = rest.lastIndexOf(' ', 180);
      out.push(rest.slice(0, cut > 40 ? cut : 180)); rest = rest.slice(cut > 40 ? cut : 180).trim();
    }
    if (rest) out.push(rest);
  }
  return out;
}

/** parts = [{ text, lang }]. Speaks them in order. onend fires when finished or stopped. */
export function speakParts(parts, onend) {
  stop();
  if (!supported) { notice('Read aloud is not supported in this browser.'); if (onend) onend(); return false; }
  const my = ++token;
  const queue = [];
  parts.forEach((p) => chunks(p.text).forEach((c) => queue.push({ text: c, lang: p.lang || store.lang })));
  let warned = false;
  const next = () => {
    if (my !== token) return;
    const item = queue.shift();
    if (!item) { if (onend) onend(); return; }
    const u = new SpeechSynthesisUtterance(item.text);
    u.lang = LANG[item.lang] || item.lang;
    const v = voiceFor(item.lang);
    if (v) u.voice = v;
    else if (item.lang !== 'en' && !warned) { warned = true; notice(t('no_voice')); }
    u.rate = 0.92;
    u.onend = next; u.onerror = next;
    speechSynthesis.speak(u);
  };
  next();
  return true;
}

export function stop() {
  token++;
  if (supported) speechSynthesis.cancel();
}

/** A 🔊 button. getParts returns the [{text, lang}] list to read. Clicking again stops. */
export function listenButton(getParts, cls = 'pill') {
  const btn = document.createElement('button');
  btn.type = 'button'; btn.className = cls;
  const idle = () => { btn.textContent = '🔊 ' + t('listen'); btn.setAttribute('aria-pressed', 'false'); delete btn.dataset.on; };
  idle();
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (btn.dataset.on) { stop(); idle(); return; }
    btn.dataset.on = '1'; btn.textContent = '⏹ ' + t('stop'); btn.setAttribute('aria-pressed', 'true');
    speakParts(getParts(), idle);
  });
  btn.addEventListener('pointerdown', (e) => e.stopPropagation());
  return btn;
}

export function toggleAutoRead() { store.autoread = !store.autoread; save(); if (!store.autoread) stop(); return store.autoread; }
