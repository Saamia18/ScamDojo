import { store, save } from './store.js';
import { t, applyLang, LANGS } from './i18n.js';
import { h, clear, initTips } from './ui.js';
import { toggleSound } from './sound.js';
import { toggleAutoRead, stop as stopSpeech } from './speech.js';
import { acct, init as initAccount, onAccount } from './account.js';
import { at } from './account_text.js';

const ROUTES = {
  home: () => import('./pages/home.js'), account: () => import('./pages/account.js'), scan: () => import('./pages/scan.js'), play: () => import('./pages/play.js'),
  duel: () => import('./pages/duel.js'), rush: () => import('./pages/rush.js'), daily: () => import('./pages/daily.js'),
  protect: () => import('./pages/protect.js'), progress: () => import('./pages/progress.js'), hood: () => import('./pages/hood.js'),
};
const NAV = [['home', 'nav_home'], ['scan', 'nav_scan'], ['play', 'nav_play'], ['duel', 'nav_duel'], ['rush', 'nav_rush'], ['protect', 'nav_protect'], ['progress', 'nav_progress'], ['hood', 'nav_hood']];
let cleanup = null, token = 0;

function parse() {
  const [route, ...rest] = (location.hash.replace(/^#\/?/, '') || 'home').split('/');
  return { route: ROUTES[route] ? route : 'home', params: rest };
}

function chrome(active) {
  const tabs = document.getElementById('tabs');
  clear(tabs).append(...NAV.map(([r, k]) => h('a', { href: '#/' + r, 'aria-current': r === active ? 'page' : null }, t(k))));
  const tools = document.getElementById('tools');
  clear(tools);
  LANGS.forEach(([code, label]) => tools.append(h('button', { class: 'pill', type: 'button', 'aria-pressed': String(store.lang === code), 'aria-label': 'Language ' + label,
    onclick: () => { store.lang = code; save(); applyLang(); go(); } }, label)));
  const who = acct.user ? acct.user.display_name.slice(0, 10) : at('nav');
  tools.append(h('a', { class: 'pill', href: '#/account', 'aria-label': acct.user ? acct.user.username : at('nav'), 'aria-current': active === 'account' ? 'page' : null }, '👤 ' + who));
  tools.append(h('button', { class: 'pill', type: 'button', title: t('autoread'), 'aria-label': t('autoread'), 'aria-pressed': String(store.autoread), onclick: (e) => { const on = toggleAutoRead(); e.currentTarget.setAttribute('aria-pressed', String(on)); } }, '🗣️'));
  tools.append(h('button', { class: 'pill', type: 'button', 'aria-label': 'Sound', 'aria-pressed': String(store.sound), onclick: (e) => { const on = toggleSound(); e.currentTarget.textContent = on ? '🔊' : '🔇'; e.currentTarget.setAttribute('aria-pressed', String(on)); } }, store.sound ? '🔊' : '🔇'));
  clear(document.getElementById('footer')).append(h('p', {}, t('disclaimer')));
}

async function go() {
  const my = ++token;
  stopSpeech();
  if (cleanup) { try { cleanup(); } catch (e) { /* ignore */ } cleanup = null; }
  const { route, params } = parse();
  chrome(route);
  const app = clear(document.getElementById('app'));
  try {
    const mod = await ROUTES[route]();
    if (my !== token) return;
    cleanup = (await mod.render(app, params)) || null;
  } catch (e) {
    app.append(h('section', { class: 'wrap page' }, h('div', { class: 'note warn' }, '⚠️ ' + e.message)));
    console.error(e);
  }
  window.scrollTo(0, 0);
}

applyLang();
initTips();
window.addEventListener('hashchange', go);
let lastIn = false;
onAccount(() => { if (!!acct.user !== lastIn) { lastIn = !!acct.user; chrome(parse().route); } });
// restore a saved session (and its language) before the first screen is drawn, but never wait long
Promise.race([initAccount(), new Promise((r) => setTimeout(r, 1500))]).finally(() => { applyLang(); lastIn = !!acct.user; go(); });
import('./pages/chat.js').then((m) => m.mount(document.getElementById('chat-root'))).catch(() => {});

// offline support: cache the app shell (see sw.js). Needs HTTPS, except on localhost.
if ('serviceWorker' in navigator && (location.protocol === 'https:' || ['localhost', '127.0.0.1'].includes(location.hostname))) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => { /* offline mode is optional */ }));
}
