// Beat the AI: a red-flag RACE. You and the engine hunt the same message at the same time.
// The engine "claims" its real findings (its highlights) one by one on a timer. Tap a suspicious part before it does.
import { h, clear, highlighted, legend } from '../ui.js';
import { getCards } from '../api.js';
import { t } from '../i18n.js';
import { store, save, addXP, markActive, recordAnswer, checkBadges } from '../store.js';
import { pickDeck } from '../deck.js';
import { play } from '../sound.js';
import { shareImage } from '../share.js';
import { localize } from '../loc.js';

const ROUNDS = 8, SECONDS = 20;
const isReal = (hl) => hl.kind === 'rule' || hl.kind === 'link';

function words(text) {
  const out = []; const re = /\S+/g; let m;
  while ((m = re.exec(text))) out.push({ text: m[0], start: m.index, end: m.index + m[0].length });
  return out;
}

export async function render(root, params = []) {
  if (params[0] === 'live') return (await import('./duel_live.js')).render(root, params.slice(1));
  const data = await getCards();
  let cleanup = () => {};
  const start = () => { cleanup(); clear(root); cleanup = match(root, data, start); window.scrollTo(0, 0); };
  intro(root, start);
  return () => cleanup();
}

function intro(root, start) {
  root.append(h('section', { class: 'page wrap', style: { maxWidth: '640px' } },
    h('h1', {}, '🤖 ' + t('duel_title')), h('p', { class: 'lead muted' }, t('duel_sub')),
    h('div', { class: 'note' }, h('ul', { style: { margin: 0, paddingLeft: '20px' } },
      h('li', {}, 'A message appears. After a few seconds the AI starts claiming its red flags, one by one (20 seconds per message).'),
      h('li', {}, 'Tap a suspicious part before the AI claims it: +2 points for you. Tap something harmless: −1.'),
      h('li', {}, 'Some messages are genuine. Press "Looks clean" for +2, but not if there really are flags.'),
      h('li', {}, 'Highest score after ' + ROUNDS + ' messages wins.'))),
    h('p', {}, h('span', { class: 'chip' }, '🏆 Duels won: ' + store.duelWins + '/' + store.duelPlayed)),
    h('div', { class: 'row' }, h('button', { class: 'btn big', type: 'button', onclick: start }, '🤖 ' + t('play_now')), h('a', { class: 'btn big ghost', href: '#/duel/live' }, '👥 Play a friend live'))));
}

function match(root, data, restart) {
  const pool = data.cards.filter((c) => !c.scam || c.ai.highlights.some(isReal));
  const deck = pickDeck(pool, ROUNDS - 2, 2).map(localize);
  const S = { round: 0, you: 0, ai: 0, log: [] };
  let overlay = null, timer = 0, stopped = false;

  const youTxt = h('b', {}, '0'), aiTxt = h('b', {}, '0'), youBar = h('i', { style: { background: 'var(--ink)' } }), aiBar = h('i', { style: { background: 'var(--rani)' } });
  const roundChip = h('span', { class: 'chip' }), timerFill = h('i', { style: { width: '100%' } });
  const status = h('div', { class: 'small', style: { minHeight: '22px', fontWeight: '700' }, 'aria-live': 'polite' });
  const arena = h('div'), reveal = h('div');
  const board = h('div', { class: 'card' },
    h('div', { class: 'row', style: { justifyContent: 'space-between' } }, h('span', {}, '🧑 You '), youTxt, roundChip, h('span', {}, '🤖 AI '), aiTxt),
    h('div', { class: 'grid cols-2', style: { gap: '8px', marginTop: '8px' } }, h('div', { class: 'meter' }, youBar), h('div', { class: 'meter' }, aiBar)),
    h('div', { class: 'meter timer', style: { marginTop: '10px' } }, timerFill));
  root.append(h('section', { class: 'page wrap', style: { maxWidth: '640px' } }, h('h1', {}, '🤖 ' + t('duel_title')), board, arena, status, reveal));

  const bars = () => {
    const top = Math.max(10, S.you, S.ai);
    youTxt.textContent = S.you; aiTxt.textContent = S.ai;
    youBar.style.width = Math.max(0, S.you) / top * 100 + '%'; aiBar.style.width = Math.max(0, S.ai) / top * 100 + '%';
    roundChip.textContent = Math.min(S.round, ROUNDS) + '/' + ROUNDS;
  };

  function nextRound() {
    if (stopped) return;
    if (S.round >= ROUNDS) return end();
    const card = deck[S.round++];
    clear(reveal); status.textContent = '';
    runRound(card);
    bars();
  }

  function runRound(card) {
    const spans = card.ai.highlights.filter(isReal).map((s) => ({ ...s, owner: null }));
    const toks = words(card.text);
    const spanOf = toks.map((tk) => spans.findIndex((sp) => tk.start < sp.end && sp.start < tk.end));
    const tokEls = toks.map((tk, i) => h('span', { class: 'tok', role: 'button', tabindex: '0' }, tk.text));
    const body = h('div', { class: 'msgview' });
    tokEls.forEach((el, i) => { body.append(el); if (i < tokEls.length - 1) body.append(' '); });
    const doneBtn = h('button', { class: 'btn ghost', type: 'button' }, '✋ Done');
    const cleanBtn = h('button', { class: 'btn legit', type: 'button' }, '✅ Looks clean');
    clear(arena).append(h('div', { class: 'stack' },
      h('div', { class: 'swipe', style: { width: '100%', cursor: 'default' } }, h('div', { class: 'sender' }, (card.channel === 'sms' ? '✉️ ' : '💬 ') + card.sender), h('div', { class: 'bubble' }, body)),
      h('div', { class: 'controls' }, cleanBtn, doneBtn)));

    // AI schedule: claims its findings one by one, in a random order
    const order = spans.map((_, i) => i).sort(() => Math.random() - 0.5);
    const when = order.map((si, k) => ({ si, at: 4 + k * 2.8 + Math.random() * 1.2 }));
    let elapsed = 0, ended = false, wrong = 0;

    const paint = (si) => {
      toks.forEach((tk, i) => { if (spanOf[i] === si) { tokEls[i].classList.remove('on'); tokEls[i].style.background = spans[si].owner === 'you' ? 'var(--sky)' : 'var(--rani-soft)'; tokEls[i].style.outline = '2px solid ' + (spans[si].owner === 'you' ? 'var(--ink)' : 'var(--rani)'); } });
    };
    const claim = (si, who) => {
      if (spans[si].owner || ended) return;
      spans[si].owner = who; paint(si);
      if (who === 'you') { S.you += 2; play('crit'); status.textContent = '🧑 You found: ' + spans[si].label; status.style.color = 'var(--ink)'; }
      else if (card.scam) { S.ai += 1; status.textContent = '🤖 The AI claimed: ' + spans[si].label; status.style.color = 'var(--rani)'; play('tap'); }
      else { spans[si].owner = 'ai'; status.textContent = '🤖 The AI thinks it found something…'; status.style.color = 'var(--rani)'; }
      bars();
      if (spans.every((s) => s.owner)) finishRound('all');
    };
    tokEls.forEach((el, i) => el.addEventListener('click', () => {
      if (ended) return;
      const si = spanOf[i];
      if (si < 0) { wrong++; S.you = Math.max(0, S.you - 1); el.style.background = 'var(--chilli-soft)'; el.style.textDecoration = 'line-through'; status.textContent = '❌ Not a red flag (−1)'; status.style.color = 'var(--chilli)'; play('bad'); bars(); }
      else if (!card.scam) { /* flag on a genuine card: engine false alarm, claim it for the AI side */ claim(si, 'you'); }
      else claim(si, 'you');
    }));
    doneBtn.addEventListener('click', () => finishRound('done'));
    cleanBtn.addEventListener('click', () => finishRound('clean'));

    clearInterval(timer);
    timer = setInterval(() => {
      if (ended || stopped) return;
      elapsed += 0.1;
      timerFill.style.width = Math.max(0, 1 - elapsed / SECONDS) * 100 + '%';
      timerFill.style.background = elapsed > SECONDS - 3 ? 'var(--chilli)' : 'var(--marigold)';
      for (const w of when) if (!spans[w.si].owner && elapsed >= w.at) claim(w.si, 'ai');
      if (elapsed >= SECONDS) finishRound('time');
    }, 100);

    function finishRound(how) {
      if (ended) return;
      ended = true; clearInterval(timer);
      let note;
      const youFound = spans.filter((s) => s.owner === 'you').length;
      if (how === 'clean') {
        if (!card.scam) { S.you += 2; note = '✅ Right: this one is genuine. +2'; play('good'); }
        else { S.you = Math.max(0, S.you - 1); note = '❌ This was a scam. The AI would have flagged ' + spans.length + '. −1'; spans.forEach((s) => { if (!s.owner) { s.owner = 'ai'; S.ai += 1; } }); play('bad'); }
      } else {
        spans.forEach((s) => { if (!s.owner) { s.owner = 'ai'; if (card.scam) S.ai += 1; } });
        note = card.scam ? '🏁 Round over. You found ' + youFound + ' of ' + spans.length + '.' : (youFound ? '⚠️ This message was genuine. Tapping flags on it was a false alarm.' : '🏁 Round over.');
      }
      const correct = card.scam ? youFound > 0 : how === 'clean';
      recordAnswer(card, correct, false); markActive();
      S.log.push({ card, found: youFound, total: spans.length });
      bars();
      status.textContent = '';
      clear(arena).append(h('div', { class: 'reveal ' + (correct ? 'good' : 'bad') },
        h('h2', {}, note),
        h('div', { class: 'bubble', style: { margin: '8px 0' } }, highlighted(card.text, card.ai.highlights)), legend(),
        spans.length ? h('div', { class: 'row', style: { margin: '8px 0' } }, spans.map((s) => h('span', { class: 'chip' }, (s.owner === 'you' ? '🧑 ' : '🤖 ') + s.label))) : null,
        h('p', {}, h('b', {}, t('lesson') + ': '), card.lesson),
        h('div', { class: 'row', style: { justifyContent: 'flex-end' } }, h('button', { class: 'btn', type: 'button', id: 'nextBtn', onclick: nextRound }, S.round >= ROUNDS ? t('finish') : t('next')))));
      const nb = arena.querySelector('#nextBtn'); if (nb) nb.focus({ preventScroll: true });
    }
  }

  function end() {
    clearInterval(timer);
    const won = S.you > S.ai, tie = S.you === S.ai;
    store.duelPlayed++; if (won) store.duelWins++;
    addXP(S.you * 2 + (won ? 20 : 0)); save();
    const fresh = checkBadges(); play(won ? 'win' : 'bad');
    clear(arena);
    overlay = h('div', { class: 'overlay', role: 'dialog', 'aria-modal': 'true' },
      h('div', { class: 'card stack' },
        h('h2', {}, won ? '🏆 You beat the AI!' : tie ? '🤝 A tie' : '🤖 The AI wins this match'),
        h('p', { class: 'display', style: { fontSize: '2rem', margin: 0 } }, 'You ' + S.you + ' – AI ' + S.ai),
        h('p', { class: 'small muted' }, 'You found ' + S.log.reduce((a, x) => a + x.found, 0) + ' of ' + S.log.reduce((a, x) => a + x.total, 0) + ' red flags across ' + ROUNDS + ' messages.'),
        fresh.length ? h('p', {}, fresh.map((b) => b.icon + ' ' + b.title + '  ')) : null,
        h('div', { class: 'row' },
          h('button', { class: 'btn small ghost', type: 'button', onclick: () => shareImage({ title: 'Red-flag race vs the AI', big: S.you + '–' + S.ai, lines: [won ? 'I beat the AI!' : 'Rematch soon.', ROUNDS + ' messages, 1 winner'], accent: '#D6247F' }) }, '📤 ' + t('share')),
          h('button', { class: 'btn', type: 'button', onclick: () => { overlay.remove(); restart(); } }, t('again')),
          h('a', { class: 'btn ghost', href: '#/progress' }, t('nav_progress')))));
    document.body.append(overlay);
  }

  bars(); nextRound();
  return () => { stopped = true; clearInterval(timer); if (overlay) overlay.remove(); };
}
