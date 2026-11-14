// Scam of the day: one card, same for everyone that day. Finishing it keeps your streak alive.
import { h, clear } from '../ui.js';
import { getCards } from '../api.js';
import { t } from '../i18n.js';
import { store, save, addXP, markActive, recordAnswer, checkBadges, streakDays, today } from '../store.js';
import { mountCard, revealPanel } from '../card.js';
import { play } from '../sound.js';
import { localize } from '../loc.js';

export async function render(root) {
  const data = await getCards();
  const cards = data.cards.slice().sort((a, b) => (a.id < b.id ? -1 : 1));
  const day = Math.floor(Date.parse(today() + 'T00:00:00Z') / 86400000);
  const card = localize(cards[(day * 7) % cards.length]);
  const done = store.daily[today()];
  const stage = h('div', { class: 'stage' }), reveal = h('div');
  const scamBtn = h('button', { class: 'btn scam', type: 'button' }, '← ' + t('swipe_scam'));
  const legitBtn = h('button', { class: 'btn legit', type: 'button' }, t('swipe_legit') + ' →');
  const controls = h('div', { class: 'controls' }, scamBtn, legitBtn);
  let ctrl = null;

  root.append(h('section', { class: 'page wrap', style: { maxWidth: '640px' } },
    h('h1', {}, '📅 ' + t('daily_title')),
    h('p', { class: 'muted' }, '🔥 ' + streakDays() + ' ' + t('days')),
    stage, controls, reveal));

  function finish(guess) {
    const correct = (guess === 'scam') === card.scam;
    store.daily[today()] = { correct }; addXP(correct ? 15 : 5); recordAnswer(card, correct, false); markActive();
    const fresh = checkBadges(); play(correct ? 'good' : 'bad');
    controls.classList.add('hide'); clear(stage);
    clear(reveal).append(revealPanel({ card, guess, correct, notes: ['🔥 ' + streakDays() + ' ' + t('days')].concat(fresh.map((b) => b.icon + ' ' + b.title)) }),
      h('div', { class: 'row', style: { marginTop: '14px' } }, h('a', { class: 'btn', href: '#/duel' }, '🤖 ' + t('duel_title')), h('a', { class: 'btn ghost', href: '#/play' }, t('play_title'))));
  }
  if (done) {
    controls.classList.add('hide');
    reveal.append(h('div', { class: 'card' }, h('h2', {}, done.correct ? '✅ ' + t('correct') : '❌ ' + t('missed')), h('p', {}, 'Come back tomorrow for a new one. In the meantime, keep training:'),
      h('div', { class: 'row' }, h('a', { class: 'btn', href: '#/duel' }, '🤖 ' + t('duel_title')), h('a', { class: 'btn ghost', href: '#/play' }, t('play_title')), h('a', { class: 'btn ghost', href: '#/rush' }, '⚡ ' + t('rush_title')))));
    return;
  }
  ctrl = mountCard(stage, card, { seconds: 0, flaggable: false, onAnswer: finish });
  scamBtn.addEventListener('click', () => ctrl.answer('scam'));
  legitBtn.addEventListener('click', () => ctrl.answer('legit'));
  const onKey = (e) => { if (ctrl && !ctrl.isDone()) { if (e.key === 'ArrowLeft') ctrl.answer('scam'); else if (e.key === 'ArrowRight') ctrl.answer('legit'); } };
  document.addEventListener('keydown', onKey);
  return () => { document.removeEventListener('keydown', onKey); if (ctrl) ctrl.destroy(); };
}
