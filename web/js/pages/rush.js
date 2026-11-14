// Inbox Rush: endless messages, a shrinking timer, one wallet. Adaptive: weak spots come back more often.
import { h, clear, inr, floatText, sleep } from '../ui.js';
import { getCards } from '../api.js';
import { t } from '../i18n.js';
import { store, save, addXP, markActive, recordAnswer, checkBadges } from '../store.js';
import { mountCard } from '../card.js';
import { endlessPicker } from '../deck.js';
import { play } from '../sound.js';
import { shareImage } from '../share.js';
import { localize } from '../loc.js';

const WALLET = 10000;

export async function render(root) {
  const data = await getCards();
  let cleanup = () => {};
  const start = () => { cleanup(); clear(root); cleanup = run(root, data, start); window.scrollTo(0, 0); };
  intro(root, start);
  return () => cleanup();
}

function intro(root, start) {
  root.append(h('section', { class: 'page wrap', style: { maxWidth: '640px' } },
    h('h1', {}, '⚡ ' + t('rush_title')), h('p', { class: 'lead muted' }, t('rush_sub')),
    h('div', { class: 'note' }, h('ul', { style: { margin: 0, paddingLeft: '20px' } },
      h('li', {}, 'Start with ₹10,000. A missed scam costs the amount a victim would lose.'),
      h('li', {}, 'Blocking a real message costs ₹500. The timer shrinks with every right answer, from 12 seconds down to 5.'),
      h('li', {}, 'Swipe, use the buttons, or press ← and →. The game ends when your wallet is empty.'))),
    h('p', {}, h('span', { class: 'chip' }, '🏅 Best: ' + store.rushBest)),
    h('button', { class: 'btn big', type: 'button', onclick: start }, t('play_now'))));
}

function run(root, data, restart) {
  const next = endlessPicker(data.cards);
  const S = { wallet: WALLET, score: 0, streak: 0, phase: 'card', ctrl: null, missed: [], over: false };
  let overlay = null, stopped = false;
  const walFill = h('i'), walTxt = h('span'), timerFill = h('i', { style: { width: '100%' } });
  const scoreChip = h('span', { class: 'chip' }), streakChip = h('span', { class: 'chip' }), bestChip = h('span', { class: 'chip' });
  const stage = h('div', { class: 'stage' });
  const flash = h('div', { class: 'small', style: { textAlign: 'center', minHeight: '24px', fontWeight: '700' }, 'aria-live': 'polite' });
  const scamBtn = h('button', { class: 'btn scam', type: 'button' }, '← ' + t('swipe_scam'));
  const legitBtn = h('button', { class: 'btn legit', type: 'button' }, t('swipe_legit') + ' →');

  root.append(h('section', { class: 'page wrap', style: { maxWidth: '640px' } },
    h('div', { class: 'card' },
      h('div', { class: 'wallet' }, h('div', { class: 'lbl' }, h('span', {}, '👛 ' + t('wallet')), walTxt), h('div', { class: 'meter' }, walFill)),
      h('div', { class: 'timer', style: { marginTop: '8px' } }, h('div', { class: 'meter' }, timerFill)),
      h('div', { class: 'row', style: { marginTop: '10px' } }, scoreChip, streakChip, bestChip)),
    stage, flash, h('div', { class: 'controls' }, scamBtn, legitBtn)));

  const secs = () => Math.max(5, 12 - 0.15 * S.score);
  function hud() {
    walFill.style.width = S.wallet / WALLET * 100 + '%'; walTxt.textContent = inr(S.wallet);
    scoreChip.textContent = '✅ ' + S.score; streakChip.textContent = '🔥 ' + S.streak; bestChip.textContent = '🏅 ' + Math.max(store.rushBest, S.score);
  }
  function showCard() {
    if (stopped || S.over) return;
    const card = localize(next());
    S.phase = 'card';
    S.ctrl = mountCard(stage, card, { seconds: secs(), timerFill, flaggable: false, onAnswer: (g) => handle(card, g) });
    hud();
  }
  async function handle(card, guess) {
    S.phase = 'wait';
    const correct = (guess === 'scam' && card.scam) || (guess === 'legit' && !card.scam);
    recordAnswer(card, correct, false); markActive();
    if (correct) { S.score++; S.streak++; play('good'); flash.textContent = '✅ ' + (card.scam ? 'Scam blocked' : 'Real message, good call'); flash.style.color = 'var(--leaf)'; }
    else {
      S.streak = 0; play('bad');
      let loss = 0;
      if (card.scam) loss = card.loss; else if (guess === 'scam') loss = 500;
      S.wallet = Math.max(0, S.wallet - loss);
      if (loss) floatText('−' + inr(loss), 'loss');
      flash.textContent = '❌ ' + (guess === 'timeout' ? 'Too slow. ' : '') + card.lesson; flash.style.color = 'var(--chilli)';
      if (S.missed.length < 6 && !S.missed.find((m) => m.id === card.id)) S.missed.push(card);
    }
    hud();
    if (S.wallet <= 0) { S.over = true; await sleep(700); return end(); }
    await sleep(correct ? 450 : 1400);
    clear(stage); flash.textContent = '';
    showCard();
  }
  function end() {
    if (stopped) return;
    const newBest = S.score > store.rushBest;
    if (newBest) store.rushBest = S.score;
    addXP(S.score * 2); save();
    const fresh = checkBadges();
    play('lose');
    overlay = h('div', { class: 'overlay', role: 'dialog', 'aria-modal': 'true' },
      h('div', { class: 'card stack' },
        h('h2', {}, '💸 ' + t('defeat')),
        h('p', { class: 'display', style: { fontSize: '2rem', margin: 0 } }, S.score + ' ✅'),
        newBest ? h('p', {}, '🏅 New personal best!') : h('p', { class: 'muted' }, 'Best: ' + store.rushBest),
        S.missed.length ? h('div', {}, h('b', {}, 'Lessons from what you missed:'), h('ul', {}, S.missed.slice(0, 4).map((c) => h('li', { class: 'small' }, c.lesson)))) : null,
        fresh.length ? h('p', {}, fresh.map((b) => b.icon + ' ' + b.title + '  ')) : null,
        h('div', { class: 'row' },
          h('button', { class: 'btn small ghost', type: 'button', onclick: () => shareImage({ title: 'Inbox Rush', big: String(S.score), lines: ['messages judged right before my wallet ran out'], accent: '#E2362F' }) }, '📤 ' + t('share')),
          h('button', { class: 'btn', type: 'button', onclick: () => { overlay.remove(); restart(); } }, t('again')),
          h('a', { class: 'btn ghost', href: '#/progress' }, t('nav_progress')))));
    document.body.append(overlay);
  }
  scamBtn.addEventListener('click', () => S.phase === 'card' && S.ctrl.answer('scam'));
  legitBtn.addEventListener('click', () => S.phase === 'card' && S.ctrl.answer('legit'));
  const onKey = (e) => { if (S.phase !== 'card' || (overlay && overlay.isConnected)) return; if (e.key === 'ArrowLeft') S.ctrl.answer('scam'); else if (e.key === 'ArrowRight') S.ctrl.answer('legit'); };
  document.addEventListener('keydown', onKey);
  showCard();
  return () => { stopped = true; document.removeEventListener('keydown', onKey); if (S.ctrl) S.ctrl.destroy(); if (overlay) overlay.remove(); };
}
