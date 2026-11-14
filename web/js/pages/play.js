// Boss Rush: five scammer bosses, a wallet to protect, tap-the-red-flags critical hits, power-ups, adaptive decks.
import { h, clear, inr, floatText, toast } from '../ui.js';
import { getCards, generateCards } from '../api.js';
import { acct } from '../account.js';
import { t } from '../i18n.js';
import { store, save, addXP, markActive, recordAnswer, checkBadges, today } from '../store.js';
import { mountCard, revealPanel } from '../card.js';
import { pickDeck } from '../deck.js';
import { play } from '../sound.js';
import { shareImage } from '../share.js';
import { localize, bossText } from '../loc.js';

const WALLET = 10000, DECK = 8, SECONDS = 16;
const TAUNT = {
  en: { hit: ['Ow!', 'Not the red flags!', 'You saw that?!', 'Grr…'], miss: 'Hehe, thanks for the cash!', real: 'That one was real. Thanks for the help!' },
  hi: { hit: ['आउच!', 'लाल झंडे मत दिखाओ!', 'तुमने वो देख लिया?!', 'ग्रर…'], miss: 'हेहे, पैसों के लिए शुक्रिया!', real: 'वो असली था। मदद के लिए शुक्रिया!' },
  kn: { hit: ['ಆಹ್!', 'ಕೆಂಪು ಬಾವುಟ ತೋರಿಸಬೇಡ!', 'ಅದನ್ನು ನೋಡಿದೆಯಾ?!', 'ಗ್ರ್…'], miss: 'ಹೆಹೆ, ಹಣಕ್ಕೆ ಧನ್ಯವಾದ!', real: 'ಅದು ನಿಜವಾಗಿತ್ತು. ಸಹಾಯಕ್ಕೆ ಧನ್ಯವಾದ!' },
};

export async function render(root, params) {
  const data = await getCards();
  const found = data.bosses.find((b) => b.id === params[0]);
  if (!found) return select(root, data);
  const boss = bossText(found);
  let cleanup = fight(root, data, boss, restart);
  function restart() { cleanup(); clear(root); cleanup = fight(root, data, boss, restart); window.scrollTo(0, 0); }
  return () => cleanup();
}

function select(root, data) {
  root.append(h('section', { class: 'page wrap' },
    h('h1', {}, t('play_title')),
    h('p', { class: 'lead muted' }, t('play_sub')),
    h('div', { class: 'note', style: { marginBottom: '22px' } },
      h('ul', { style: { margin: 0, paddingLeft: '20px' } },
        h('li', {}, 'Swipe left for scam, right for legit. Buttons and the ← → keys work too.'),
        h('li', {}, t('tap_flags') + ' Real red flags land a critical hit.'),
        h('li', {}, 'Miss a scam and money leaves your ₹10,000 wallet. Block a real message and the boss heals.'),
        h('li', {}, 'Hint costs 20 XP. Slow time is earned with a 3-answer streak. Cards you miss come back more often.'))),
    freshPanel(data),
    h('div', { class: 'bossgrid' }, data.bosses.map((b) => h('a', { class: 'bosscard' + (store.bossDone[b.id] ? ' done' : ''), href: '#/play/' + b.id },
      h('span', { class: 'boss' }, b.emoji), h('h3', {}, b.name), h('div', { class: 'small muted' }, bossText(b).tagline),
      h('div', { style: { marginTop: '8px' } }, store.bossDone[b.id] ? h('span', { class: 'chip' }, '✅ ' + t('done')) : h('span', { class: 'chip' }, t('play_now'))))))));
}

function fight(root, data, boss, restart) {
  const pool = data.cards.filter((c) => c.boss === boss.id);
  const deck = pickDeck(pool, 5, 3).map(localize);
  const S = { hp: boss.hp, wallet: WALLET, streak: 0, slow: 0, idx: 0, mistakes: 0, correct: 0, crits: 0, phase: 'card', ctrl: null };
  let overlay = null;

  const bossEl = h('span', { class: 'boss', 'aria-hidden': 'true' }, boss.emoji);
  const taunt = h('div', { class: 'bubble small', style: { marginTop: '6px' } }, boss.intro);
  const hpFill = h('i'), hpTxt = h('span'), walFill = h('i'), walTxt = h('span'), timerFill = h('i', { style: { width: '100%' } });
  const progress = h('span', { class: 'chip' }), streakChip = h('span', { class: 'chip' });
  const stage = h('div', { class: 'stage' });
  const reveal = h('div');
  const hintBtn = h('button', { class: 'btn small ghost', type: 'button' }), slowBtn = h('button', { class: 'btn small ghost', type: 'button' });
  const scamBtn = h('button', { class: 'btn scam', type: 'button' }, '← ' + t('swipe_scam'));
  const legitBtn = h('button', { class: 'btn legit', type: 'button' }, t('swipe_legit') + ' →');
  const controls = h('div', { class: 'controls' }, scamBtn, legitBtn);
  const powers = h('div', { class: 'powers' }, hintBtn, slowBtn);

  root.append(h('section', { class: 'page wrap', style: { maxWidth: '640px' } },
    h('a', { href: '#/play', class: 'small' }, '← ' + t('play_title')),
    h('div', { class: 'card', style: { marginTop: '10px' } },
      h('div', { class: 'bossbar' }, h('div', { style: { textAlign: 'center' } }, bossEl),
        h('div', { class: 'hp' }, h('div', { class: 'lbl' }, h('span', {}, boss.name), hpTxt), h('div', { class: 'meter' }, hpFill), taunt)),
      h('div', { class: 'hud', style: { marginTop: '14px' } },
        h('div', { class: 'wallet' }, h('div', { class: 'lbl' }, h('span', {}, '👛 ' + t('wallet')), walTxt), h('div', { class: 'meter' }, walFill)),
        h('div', { class: 'timer' }, h('div', { class: 'lbl' }, h('span', {}, '⏱'), h('span', {}, '')), h('div', { class: 'meter' }, timerFill))),
      h('div', { class: 'row', style: { marginTop: '10px' } }, progress, streakChip)),
    stage, controls, powers, reveal));

  function hud() {
    hpFill.style.width = Math.max(0, S.hp / boss.hp) * 100 + '%';
    hpTxt.textContent = Math.max(0, S.hp) + '/' + boss.hp;
    walFill.style.width = S.wallet / WALLET * 100 + '%';
    walTxt.textContent = inr(S.wallet);
    progress.textContent = Math.min(S.idx, DECK) + '/' + DECK;
    streakChip.textContent = '🔥 ' + t('streak') + ' ' + S.streak;
    hintBtn.textContent = '💡 ' + t('hint') + ' (−20 XP)';
    hintBtn.disabled = S.phase !== 'card' || store.xp < 20;
    slowBtn.textContent = '⏱ ' + t('slow') + ' ×' + S.slow;
    slowBtn.disabled = S.phase !== 'card' || S.slow < 1;
  }

  function showCard() {
    if (S.hp <= 0) return end('win');
    if (S.wallet <= 0) return end('lose');
    if (S.idx >= deck.length) return end('escaped');
    const card = deck[S.idx++];
    S.phase = 'card';
    clear(reveal);
    controls.classList.remove('hide'); powers.classList.remove('hide');
    S.ctrl = mountCard(stage, card, { seconds: SECONDS, timerFill, flaggable: true, onAnswer: (g, info) => handle(card, g, info) });
    hud();
  }

  function handle(card, guess, info) {
    S.phase = 'reveal';
    controls.classList.add('hide'); powers.classList.add('hide');
    const correct = (guess === 'scam' && card.scam) || (guess === 'legit' && !card.scam);
    const notes = [];
    let crit = 0;
    if (correct) {
      let dmg = 12;
      if (card.scam && info.flagged > 0) { crit = Math.min(2, info.flagged) * 6; dmg += crit; notes.push('🎯 ' + t('crit') + ' +' + crit); S.crits++; }
      S.hp -= dmg; S.streak++; S.correct++;
      addXP(10 + (crit ? 5 : 0));
      if (S.streak % 3 === 0 && S.slow < 2) { S.slow++; notes.push('⏱ +1 ' + t('slow')); }
      notes.push('−' + dmg + ' ' + t('boss_hp'));
      bossEl.classList.remove('hit'); void bossEl.offsetWidth; bossEl.classList.add('hit');
      taunt.textContent = (TAUNT[store.lang] || TAUNT.en).hit[S.correct % 4];
      floatText(crit ? 'CRIT −' + dmg : '−' + dmg, crit ? 'crit' : '');
      play(crit ? 'crit' : 'good');
    } else {
      S.streak = 0; S.mistakes++;
      if (card.scam) {
        S.wallet = Math.max(0, S.wallet - card.loss);
        notes.push('−' + inr(card.loss));
        floatText('−' + inr(card.loss), 'loss');
        bossEl.classList.remove('laugh'); void bossEl.offsetWidth; bossEl.classList.add('laugh');
        taunt.textContent = (TAUNT[store.lang] || TAUNT.en).miss;
      } else if (guess === 'scam') {
        S.hp = Math.min(boss.hp, S.hp + 6); notes.push('+6 ' + t('boss_hp'));
        taunt.textContent = (TAUNT[store.lang] || TAUNT.en).real;
      }
      play('bad');
    }
    recordAnswer(card, correct, crit > 0);
    markActive();
    for (const b of checkBadges()) toast(b.icon + ' ' + b.title);
    clear(stage);
    const last = S.hp <= 0 || S.wallet <= 0 || S.idx >= deck.length;
    clear(reveal).append(revealPanel({ card, guess, correct, notes, nextLabel: last ? t('finish') : t('next'), onNext: showCard }));
    const nb = reveal.querySelector('#nextBtn'); if (nb) nb.focus({ preventScroll: true });
    hud();
  }

  function end(kind) {
    S.phase = 'over';
    clear(reveal); clear(stage);
    controls.classList.add('hide'); powers.classList.add('hide');
    let title, msg;
    if (kind === 'win') {
      addXP(25); store.bossDone[boss.id] = today(); store.stats.bossWins++;
      if (S.mistakes === 0) store.perfect++;
      save(); play('win'); title = '🎉 ' + t('victory'); msg = boss.defeat;
    } else if (kind === 'lose') { play('lose'); title = '💸 ' + t('defeat'); msg = 'The ' + boss.name + ' drained your wallet. Every miss comes back sooner next time.'; }
    else { play('lose'); title = '🏃 ' + t('escaped'); msg = 'You needed to land more hits. Spot at least 6 of ' + DECK + ', or tap real red flags for critical hits.'; }
    const fresh = checkBadges();
    const idx = data.bosses.findIndex((b) => b.id === boss.id);
    const nextBoss = data.bosses[idx + 1];
    overlay = h('div', { class: 'overlay', role: 'dialog', 'aria-modal': 'true' },
      h('div', { class: 'card stack' },
        h('h2', {}, title), h('p', {}, msg),
        h('div', { class: 'row' }, h('span', { class: 'chip' }, '✅ ' + S.correct + '/' + DECK), h('span', { class: 'chip' }, '👛 ' + inr(S.wallet)), h('span', { class: 'chip' }, '🎯 ' + S.crits), h('span', { class: 'chip' }, 'XP ' + store.xp)),
        h('p', {}, h('b', {}, t('lesson') + ': '), boss.lesson),
        fresh.length ? h('p', {}, fresh.map((b) => b.icon + ' ' + b.title + '  ')) : null,
        h('div', { class: 'row' },
          kind === 'win' ? h('button', { class: 'btn small ghost', type: 'button', onclick: () => shareImage({ title: 'I beat the ' + boss.name, big: boss.emoji, lines: ['Wallet saved: ' + inr(S.wallet), S.correct + '/' + DECK + ' messages judged right'], accent: boss.color }) }, '📤 ' + t('share')) : null,
          h('button', { class: 'btn', type: 'button', onclick: () => { overlay.remove(); restart(); } }, t('again')),
          kind === 'win' && nextBoss ? h('a', { class: 'btn ink', href: '#/play/' + nextBoss.id }, nextBoss.emoji + ' ' + nextBoss.name) : null,
          h('a', { class: 'btn ghost', href: '#/play' }, t('play_title')))));
    document.body.append(overlay);
    hud();
  }

  scamBtn.addEventListener('click', () => S.phase === 'card' && S.ctrl.answer('scam'));
  legitBtn.addEventListener('click', () => S.phase === 'card' && S.ctrl.answer('legit'));
  hintBtn.addEventListener('click', () => {
    if (S.phase !== 'card') return;
    if (store.xp < 20) return toast('You need 20 XP for a hint.');
    if (S.ctrl.hint()) { addXP(-20); hud(); } else toast('No red flags found in this one…');
  });
  slowBtn.addEventListener('click', () => { if (S.phase === 'card' && S.slow > 0) { S.slow--; S.ctrl.freeze(4000); hud(); } });
  const onKey = (e) => {
    if (overlay && overlay.isConnected) return;
    if (S.phase === 'card' && e.key === 'ArrowLeft') S.ctrl.answer('scam');
    else if (S.phase === 'card' && e.key === 'ArrowRight') S.ctrl.answer('legit');
    else if (S.phase === 'reveal' && e.key === 'Enter') { const nb = reveal.querySelector('#nextBtn'); if (nb && document.activeElement !== nb) nb.click(); }
  };
  document.addEventListener('keydown', onKey);

  showCard();
  return () => { document.removeEventListener('keydown', onKey); if (S.ctrl) S.ctrl.destroy(); if (overlay) overlay.remove(); };
}

const FRESH = [['digital_arrest', 'Digital arrest (fake police)'], ['electricity', 'Electricity bill threat'], ['part_time_job', 'Part-time job'], ['kyc', 'Fake KYC'],
  ['upi_refund', 'UPI refund / QR'], ['otp', 'OTP request'], ['courier', 'Parcel / customs'], ['prize', 'Lucky draw'], ['investment', 'Investment tips']];

function freshPanel(data) {
  const generated = data.cards.filter((c) => c.generated).length;
  const box = h('div', { class: 'card stack flat', style: { marginBottom: '22px' } }, h('h3', {}, '✨ Fresh scam scenarios'),
    h('p', { class: 'small muted' }, 'New messages built from real fraud patterns so you cannot just memorise the deck. ' + (generated ? generated + ' generated so far and mixed into your decks.' : 'They are mixed into your decks automatically.')));
  if (!acct.user) return box.append(h('a', { class: 'btn small', href: '#/account' }, '👤 Log in to generate')) || box;
  const sel = h('select', { class: 'field', 'aria-label': 'Scam type' }, FRESH.map(([v, l]) => h('option', { value: v }, l)));
  const out = h('div', { class: 'small', 'aria-live': 'polite' });
  const go = h('button', { class: 'btn small', type: 'button', onclick: async () => {
    go.disabled = true; out.textContent = 'Generating…';
    try {
      const r = await generateCards(sel.value, store.lang, 2);
      r.cards.forEach((c) => { if (!data.cards.find((x) => x.id === c.id)) data.cards.push(c); });
      out.textContent = '✅ Added ' + r.cards.length + ' new card' + (r.cards.length === 1 ? '' : 's') + ' (' + (r.source === 'llm' ? 'written by an AI model' : 'built from templates') + '). They will appear in the matching boss fight.';
    } catch (e) { out.textContent = '⚠️ ' + e.message; } finally { go.disabled = false; }
  } }, 'Generate');
  box.append(h('div', { class: 'row' }, sel, go), out);
  return box;
}
