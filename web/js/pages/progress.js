import { h, pct, toast } from '../ui.js';
import { t } from '../i18n.js';
import { store, BADGES, level, streakDays, checkBadges } from '../store.js';
import { shareImage } from '../share.js';
import { acct } from '../account.js';
import { at } from '../account_text.js';

const CAT = { otp: 'OTP and PIN requests', upi: 'UPI collect requests', kyc: 'Fake KYC', threat: 'Account threats', prize: 'Prize and lottery', fee: 'Advance fees', job: 'Fake jobs',
  courier: 'Parcel and delivery', utility: 'Bill disconnection', invest: 'Investment tips', loan: 'Instant loans', authority: 'Fake police and agencies', refund: 'Refund bait',
  sim: 'SIM upgrade', remote: 'Remote-access apps', apk: 'App downloads', credential: 'Card and login details', link: 'Look-alike links', family: 'Relative in trouble', kraken: 'KYC', llama: 'Prizes', octopus: 'OTP', jackal: 'Jobs', cobra: 'Parcels' };

export function render(root) {
  checkBadges();
  const board = h('div', { class: 'card' }, h('h2', {}, '🏆 ' + at('lb_title')), h('p', { class: 'small muted' }, at('lb_note')));
  fetch('/api/leaderboard').then((r) => r.json()).then((d) => board.append(d.rows.length ? h('table', { class: 't' }, h('tr', {}, ['#', '', 'XP', 'Lv'].map((x) => h('th', {}, x))), d.rows.map((r) => h('tr', {}, h('td', {}, r.rank), h('td', { style: { textAlign: 'left' } }, r.name), h('td', {}, r.xp), h('td', {}, r.level)))) : h('p', { class: 'muted' }, '—'))).catch(() => {});
  const st = store.stats;
  const acc = st.seen ? st.correct / st.seen : 0;
  const into = store.xp % 100;
  const weak = Object.entries(store.miss).filter(([, v]) => v.seen > 0).map(([k, v]) => [k, v.miss / v.seen, v.seen]).sort((a, b) => b[1] - a[1]);

  root.append(h('section', { class: 'page wrap stack' },
    h('h1', {}, t('progress_title')),
    acct.user ? h('div', { class: 'note' }, '✅ @' + acct.user.username, ' · ', h('a', { href: '#/account' }, '👤')) : h('div', { class: 'note warn' }, '📱 ' + (store.lang === 'hi' ? 'प्रगति सिर्फ़ इस डिवाइस पर है। ' : store.lang === 'kn' ? 'ಪ್ರಗತಿ ಈ ಸಾಧನದಲ್ಲಿ ಮಾತ್ರ ಇದೆ. ' : 'Your progress is stored on this device only. '), h('a', { href: '#/account' }, '👤 ' + (store.lang === 'hi' ? 'खाता बनाएँ' : store.lang === 'kn' ? 'ಖಾತೆ ರಚಿಸಿ' : 'Create an account'))),
    h('div', { class: 'card' },
      h('div', { class: 'row' }, h('span', { class: 'display', style: { fontSize: '2rem' } }, t('level') + ' ' + level()), h('span', { class: 'chip' }, store.xp + ' XP'), h('span', { class: 'chip' }, '🔥 ' + streakDays() + ' ' + t('days'))),
      h('div', { class: 'meter', style: { margin: '10px 0' } }, h('i', { style: { width: into + '%', background: 'var(--rani)' } })),
      h('div', { class: 'row' },
        h('span', { class: 'chip' }, 'Answered ' + st.seen), h('span', { class: 'chip' }, 'Accuracy ' + pct(acc)), h('span', { class: 'chip' }, 'Bosses ' + Object.keys(store.bossDone).length + '/5'),
        h('span', { class: 'chip' }, 'Rush best ' + store.rushBest), h('span', { class: 'chip' }, 'Duels won ' + store.duelWins + '/' + store.duelPlayed)),
      h('div', { class: 'row', style: { marginTop: '12px' } },
        h('button', { class: 'btn small', type: 'button', onclick: () => shareImage({ title: 'Level ' + level() + ' scam spotter', big: pct(acc), lines: [st.seen + ' messages judged', '🔥 ' + streakDays() + ' day streak', Object.keys(store.bossDone).length + '/5 bosses beaten'], accent: '#FFB400' }) }, '📤 ' + t('share')),
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => { if (confirm('Erase all progress on this device?')) { localStorage.removeItem('scamdojo.v1'); location.reload(); } } }, 'Reset'))),
    h('div', { class: 'card' }, h('h2', {}, t('weak')),
      weak.length ? h('div', { class: 'stack' }, weak.slice(0, 8).map(([k, rate, seen]) => h('div', { class: 'signal' }, h('span', {}, CAT[k] || k), h('div', { class: 'meter' }, h('i', { style: { width: pct(rate), background: 'var(--chilli)' } })), h('b', {}, pct(rate)))), h('p', { class: 'small muted' }, 'Share of messages of this type that you got wrong. These come back more often in your next decks.'))
        : h('p', { class: 'muted' }, 'Play a round and your weak spots appear here. The game then serves you more of them.')),
    board,
    h('div', { class: 'card' }, h('h2', {}, t('badges')),
      h('div', { class: 'badges' }, BADGES.map((b) => h('div', { class: 'badge' + (store.badges[b.id] ? '' : ' locked') }, h('span', { class: 'ic' }, b.icon), h('div', {}, h('b', {}, b.title), h('div', { class: 'small muted' }, b.desc))))))));
}
