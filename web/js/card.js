// The swipeable message card and the reveal panel, shared by Boss Rush, Beat the AI, Inbox Rush and Scam of the day.
import { h, clear, highlighted, legend, pct } from './ui.js';
import { t } from './i18n.js';
import { store } from './store.js';
import { listenButton, speakParts, stop as stopSpeech, supported as speechOK } from './speech.js';

export const aiSaysScam = (card) => card.ai.risk >= 0.5;

function words(text) {
  const out = [];
  const re = /\S+/g;
  let m;
  while ((m = re.exec(text))) out.push({ text: m[0], start: m.index, end: m.index + m[0].length });
  return out;
}
const isRealFlag = (hl) => hl.kind === 'rule' || hl.kind === 'link';

export function mountCard(stage, card, { seconds = 0, timerFill = null, flaggable = false, onAnswer }) {
  const toks = words(card.text);
  const flagged = new Set();
  let done = false, raf = 0, frozenUntil = 0, remaining = seconds * 1000, last = performance.now(), held = false;
  const cardLang = card.translated ? store.lang : 'en';
  const parts = [{ text: card.text, lang: cardLang }];

  const tokEls = toks.map((tk, i) => {
    const el = h('span', { class: 'tok', role: flaggable ? 'button' : null, tabindex: flaggable ? '0' : null }, tk.text);
    if (flaggable) {
      const toggle = () => { if (done) return; flagged.has(i) ? flagged.delete(i) : flagged.add(i); el.classList.toggle('on'); };
      el.addEventListener('click', toggle);
      el.addEventListener('keydown', (e) => { if (e.key === ' ') { e.preventDefault(); toggle(); } });
    }
    return el;
  });
  const body = h('div', { class: 'msgview' });
  tokEls.forEach((el, i) => { body.append(el); if (i < tokEls.length - 1) body.append(' '); });

  const labL = h('div', { class: 'drag-lab l' }, t('swipe_scam'));
  const labR = h('div', { class: 'drag-lab r' }, t('swipe_legit'));
  const el = h('div', { class: 'swipe' }, labL, labR,
    h('div', { class: 'sender' }, (card.channel === 'sms' ? '✉️ ' : '💬 ') + card.sender, card.generated ? h('span', { class: 'chip', style: { fontSize: '.7rem', padding: '0 8px' } }, '🤖 AI-generated') : null, h('span', { class: 'grow' }), listenButton(() => parts, 'pill small')),
    h('div', { class: 'bubble' }, body));
  clear(stage).append(el);

  function finish(guess) {
    if (done) return;
    done = true;
    cancelAnimationFrame(raf);
    stopSpeech();
    el.style.cursor = 'default';
    onAnswer(guess, { flagged: realFlags() });
  }
  function realFlags() {
    const spans = card.ai.highlights.filter(isRealFlag);
    let n = 0;
    for (const sp of spans) {
      if ([...flagged].some((i) => toks[i].start < sp.end && sp.start < toks[i].end)) n++;
    }
    return n;
  }
  function fling(guess) {
    if (done) return;
    const dir = guess === 'scam' ? -1 : 1;
    el.style.transition = 'transform .25s ease-out, opacity .25s';
    el.style.transform = 'translateX(' + dir * 420 + 'px) rotate(' + dir * 18 + 'deg)';
    el.style.opacity = '0';
    finish(guess);
  }

  // ---- drag ----
  let sx = 0, dx = 0, drag = false, pid = null;
  el.addEventListener('pointerdown', (e) => { if (done) return; sx = e.clientX; dx = 0; drag = false; pid = e.pointerId; });
  el.addEventListener('pointermove', (e) => {
    if (done || pid !== e.pointerId) return;
    const d = e.clientX - sx;
    if (!drag && Math.abs(d) > 8) { drag = true; try { el.setPointerCapture(pid); } catch (err) { /* ignore */ } el.style.transition = 'none'; }
    if (!drag) return;
    dx = d;
    el.style.transform = 'translateX(' + dx + 'px) rotate(' + dx / 22 + 'deg)';
    labL.style.opacity = dx < 0 ? Math.min(1, -dx / 110) : 0;
    labR.style.opacity = dx > 0 ? Math.min(1, dx / 110) : 0;
  });
  const up = (e) => {
    if (pid !== e.pointerId) return;
    pid = null;
    if (!drag || done) return;
    if (Math.abs(dx) > 110) fling(dx < 0 ? 'scam' : 'legit');
    else { el.style.transition = 'transform .2s'; el.style.transform = ''; labL.style.opacity = labR.style.opacity = 0; }
  };
  el.addEventListener('pointerup', up);
  el.addEventListener('pointercancel', up);

  // ---- timer ----
  function tick(now) {
    if (done) return;
    const dt = now - last; last = now;
    if (!held && now >= frozenUntil) remaining -= dt;
    if (timerFill) {
      timerFill.style.width = Math.max(0, remaining / (seconds * 1000)) * 100 + '%';
      timerFill.style.background = now < frozenUntil ? 'var(--sky)' : remaining < 2500 ? 'var(--chilli)' : 'var(--marigold)';
    }
    if (remaining <= 0) { el.style.opacity = '.4'; finish('timeout'); return; }
    raf = requestAnimationFrame(tick);
  }
  if (store.autoread && speechOK) { held = true; speakParts(parts, () => { held = false; }); setTimeout(() => { held = false; }, 25000); }
  if (seconds > 0) { last = performance.now(); raf = requestAnimationFrame(tick); }

  return {
    answer: fling,
    freeze: (ms) => { frozenUntil = performance.now() + ms; },
    hint() {
      const sp = card.ai.highlights.find(isRealFlag);
      if (!sp) return false;
      toks.forEach((tk, i) => { if (tk.start < sp.end && sp.start < tk.end) tokEls[i].classList.add('hint'); });
      return true;
    },
    isDone: () => done,
    destroy() { done = true; cancelAnimationFrame(raf); stopSpeech(); },
  };
}

/** What happened on this card, plus the lesson and what the AI said. */
export function revealPanel({ card, guess, correct, notes = [], nextLabel, onNext }) {
  const ai = card.ai;
  const aiScam = aiSaysScam(card);
  const aiRight = aiScam === card.scam;
  const title = correct ? t('correct') : guess === 'timeout' ? t('timeup') : card.scam ? t('missed') : t('false_alarm');
  const label = (g) => (g === 'scam' ? t('swipe_scam') : g === 'legit' ? t('swipe_legit') : '⏱');
  const box = h('div', { class: 'reveal ' + (correct ? 'good' : 'bad'), 'aria-live': 'polite' },
    h('h2', {}, (correct ? '✅ ' : '❌ ') + title),
    notes.length ? h('div', { class: 'row', style: { marginBottom: '8px' } }, notes.map((n) => h('span', { class: 'chip' }, n))) : null,
    h('div', { class: 'aiduel' },
      h('div', {}, h('span', { class: 'small muted' }, t('you_said')), h('b', {}, label(guess))),
      h('div', {}, h('span', { class: 'small muted' }, t('ai_said')), h('b', {}, (aiScam ? t('swipe_scam') : t('swipe_legit')) + ' ' + pct(ai.risk)), h('span', { class: 'small' }, aiRight ? '✅' : '❌')),
      h('div', {}, h('span', { class: 'small muted' }, t('truth')), h('b', {}, card.scam ? t('swipe_scam') : t('swipe_legit')))),
    h('div', { class: 'bubble', style: { margin: '8px 0' } }, highlighted(card.text, ai.highlights)),
    legend(),
    h('p', { style: { marginTop: '10px' } }, h('b', {}, t('lesson') + ': '), card.lesson),
    ai.reasons && ai.reasons.length && card.scam ? h('p', { class: 'small muted' }, '🤖 ' + ai.reasons.map((r) => r.title).slice(0, 2).join(' · ')) : null,
    card.translated ? h('p', { class: 'small muted' }, 'ℹ️ ' + t('ai_note')) : null,
    onNext ? h('div', { class: 'row', style: { justifyContent: 'flex-end', marginTop: '8px' } }, h('button', { class: 'btn', type: 'button', onclick: onNext, id: 'nextBtn' }, nextLabel || t('next'))) : null);
  const rparts = [{ text: title + '.', lang: store.lang }, { text: card.lesson, lang: card.translated ? store.lang : 'en' }];
  box.insertBefore(h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, listenButton(() => rparts, 'pill small')), box.firstChild);
  if (store.autoread && speechOK) setTimeout(() => speakParts(rparts), 300);
  requestAnimationFrame(() => box.scrollIntoView({ block: 'nearest', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }));
  return box;
}
