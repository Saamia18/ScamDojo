import { h } from '../ui.js';
import { buildScanner } from '../scanner.js';
import { t } from '../i18n.js';
import { store, level, streakDays } from '../store.js';

export function render(root) {
  const out = h('div', { class: 'stack', style: { marginTop: '26px' } });
  const sample = 'Dear SBI user, your YONO account is restricted. Complete KYC today: http://yono-sbi-care.top/kyc or your account will be blocked within 2 hours.';
  const hero = h('section', { class: 'wrap', style: { paddingTop: '30px' } },
    h('div', { class: 'hero' },
      h('div', {},
        h('h1', {}, t('hero_title')),
        h('p', { class: 'lead' }, t('hero_sub')),
        h('div', { class: 'row' },
          h('span', { class: 'chip' }, 'EN · हिन्दी · ಕನ್ನಡ'), h('span', { class: 'chip' }, '👤 Login optional'), h('span', { class: 'chip' }, '🔒 Messages never stored'))),
      buildScanner(out, { initial: sample })),
    out);

  const modes = h('section', { class: 'wrap page', style: { paddingTop: '8px' } },
    h('h2', {}, t('play_title') + ' · ' + t('duel_title') + ' · ' + t('rush_title')),
    h('div', { class: 'modes' },
      mode('#/play', '🦑', t('play_title'), t('play_sub')),
      mode('#/duel', '🤖', t('duel_title'), t('duel_sub')),
      mode('#/rush', '⚡', t('rush_title'), t('rush_sub')),
      mode('#/daily', '📅', t('daily_title'), '1')),
    h('div', { class: 'row', style: { marginTop: '18px' } },
      h('span', { class: 'chip' }, t('level') + ' ' + level()), h('span', { class: 'chip' }, store.xp + ' XP'),
      h('span', { class: 'chip' }, '🔥 ' + streakDays() + ' ' + t('days'))));
  root.append(hero, modes);
}

function mode(href, icon, title, sub) {
  return h('a', { class: 'mode', href }, h('div', { class: 'big' }, icon), h('h3', { style: { marginTop: '8px' } }, title), h('div', { class: 'muted small' }, sub === '1' ? '' : sub));
}
