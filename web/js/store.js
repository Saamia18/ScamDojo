// Progress lives in this browser only (localStorage). No account, no server-side storage.
const KEY = 'scamdojo.v1';
const defaults = () => ({
  lang: 'en', sound: true, autoread: false, checkups: [], saveHistory: false, leaderboard: false, xp: 0, days: [], bossDone: {}, rushBest: 0, duelWins: 0, duelPlayed: 0,
  stats: { seen: 0, correct: 0, crits: 0, bossWins: 0 }, miss: {}, cats: { otp: 0, link: 0 }, perfect: 0, badges: {}, daily: {},
});

export const store = defaults();

try {
  const saved = JSON.parse(localStorage.getItem(KEY) || 'null');
  if (saved && typeof saved === 'object') {
    const d = defaults();
    Object.assign(store, d, saved, { stats: { ...d.stats, ...(saved.stats || {}) }, cats: { ...d.cats, ...(saved.cats || {}) } });
  }
} catch (e) { /* storage unavailable: run in memory */ }

let saveHook = null;
export const setSaveHook = (f) => { saveHook = f; };
export function save(noHook) {
  try { localStorage.setItem(KEY, JSON.stringify(store)); } catch (e) { /* ignore */ }
  if (!noHook && saveHook) saveHook();
}

// ---- account sync helpers ----
const SYNC_KEYS = ['lang', 'sound', 'autoread', 'saveHistory', 'leaderboard', 'xp', 'days', 'bossDone', 'rushBest', 'duelWins', 'duelPlayed', 'stats', 'miss', 'cats', 'perfect', 'badges', 'daily', 'checkups'];
export const snapshot = () => JSON.parse(JSON.stringify(Object.fromEntries(SYNC_KEYS.map((k) => [k, store[k]]))));

/** Combine saved progress from the account with progress on this device. Never loses badges, bosses or days. */
export function mergeProgress(r, takePrefs) {
  if (!r) return;
  const max = (a, b) => Math.max(a || 0, b || 0);
  for (const k of ['xp', 'rushBest', 'duelWins', 'duelPlayed', 'perfect']) store[k] = max(store[k], r[k]);
  for (const k of Object.keys(store.stats)) store.stats[k] = max(store.stats[k], (r.stats || {})[k]);
  for (const k of Object.keys(store.cats)) store.cats[k] = max(store.cats[k], (r.cats || {})[k]);
  store.days = [...new Set([...(store.days || []), ...(r.days || [])])].sort().slice(-120);
  for (const m of ['bossDone', 'badges']) for (const [k, v] of Object.entries(r[m] || {})) if (!store[m][k] || v < store[m][k]) store[m][k] = v;
  for (const [k, v] of Object.entries(r.daily || {})) if (!store.daily[k]) store.daily[k] = v;
  for (const [k, v] of Object.entries(r.miss || {})) if (!store.miss[k] || v.seen > store.miss[k].seen) store.miss[k] = v;
  const seen = new Set(), all = [];
  for (const c of [...(store.checkups || []), ...(r.checkups || [])]) { const id = c.date + ':' + c.good + ':' + c.total; if (!seen.has(id)) { seen.add(id); all.push(c); } }
  store.checkups = all.sort((a, b) => (a.date < b.date ? -1 : 1)).slice(-20);
  if (takePrefs) { if (['en', 'hi', 'kn'].includes(r.lang)) store.lang = r.lang; store.sound = r.sound !== false; store.autoread = !!r.autoread; store.saveHistory = !!r.saveHistory; store.leaderboard = !!r.leaderboard; }
}

/** Forget everything on this device (used when logging out or deleting an account). */
export function wipeLocal() {
  Object.assign(store, defaults(), { lang: store.lang });
  try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
}

export const today = () => new Date().toISOString().slice(0, 10);
const dayNum = (iso) => Math.floor(Date.parse(iso + 'T00:00:00Z') / 86400000);

export function markActive() {
  const d = today();
  if (!store.days.includes(d)) { store.days.push(d); store.days = store.days.slice(-120); }
  save();
}
export function streakDays() {
  const set = new Set(store.days.map(dayNum));
  let n = dayNum(today());
  if (!set.has(n)) n -= 1;
  let streak = 0;
  while (set.has(n)) { streak++; n--; }
  return streak;
}
export const level = () => 1 + Math.floor(store.xp / 100);

export const BADGES = [
  { id: 'first', icon: '🥋', title: 'First belt', desc: 'Answer your first message.', ok: (s) => s.stats.seen >= 1 },
  { id: 'otp', icon: '🛡️', title: 'OTP Guardian', desc: 'Correctly block 10 OTP or UPI-PIN scams.', ok: (s) => s.cats.otp >= 10 },
  { id: 'link', icon: '🔍', title: 'Link Detective', desc: 'Correctly block 10 scams that hide behind a fake link.', ok: (s) => s.cats.link >= 10 },
  { id: 'crit', icon: '🎯', title: 'Sharp eye', desc: 'Land 10 critical hits by tapping real red flags.', ok: (s) => s.stats.crits >= 10 },
  { id: 'kraken', icon: '🦑', title: 'KYC Slayer', desc: 'Defeat the KYC Kraken.', ok: (s) => !!s.bossDone.kraken },
  { id: 'hunter', icon: '🏆', title: 'Boss Hunter', desc: 'Defeat all five bosses.', ok: (s) => ['kraken', 'llama', 'octopus', 'jackal', 'cobra'].every((b) => s.bossDone[b]) },
  { id: 'perfect', icon: '💯', title: 'Flawless', desc: 'Beat a boss without a single mistake.', ok: (s) => s.perfect >= 1 },
  { id: 'speed', icon: '⚡', title: 'Speed demon', desc: 'Get 25 right in one Inbox Rush.', ok: (s) => s.rushBest >= 25 },
  { id: 'ai', icon: '🤖', title: 'AI beater', desc: 'Score higher than the AI in a duel.', ok: (s) => s.duelWins >= 1 },
  { id: 'streak3', icon: '🔥', title: 'Three-day streak', desc: 'Train three days in a row.', ok: () => streakDays() >= 3 },
  { id: 'streak7', icon: '🌟', title: 'Seven-day streak', desc: 'Train seven days in a row.', ok: () => streakDays() >= 7 },
];

/** Re-check badges. Returns the newly earned ones so the UI can celebrate. */
export function checkBadges() {
  const fresh = [];
  for (const b of BADGES) {
    if (!store.badges[b.id] && b.ok(store)) { store.badges[b.id] = today(); fresh.push(b); }
  }
  if (fresh.length) save();
  return fresh;
}

export function addXP(n) { store.xp = Math.max(0, store.xp + n); save(); }

export function primaryCategory(card) {
  const cats = (card.ai && card.ai.categories) || [];
  return cats.find((c) => c !== 'link') || cats[0] || card.boss;
}

/** Remember which scam types the player misses, so later decks serve more of them (adaptive difficulty). */
export function recordAnswer(card, correct, crit) {
  const cat = primaryCategory(card);
  const m = (store.miss[cat] = store.miss[cat] || { seen: 0, miss: 0 });
  m.seen++;
  if (!correct) m.miss++;
  store.stats.seen++;
  if (correct) store.stats.correct++;
  if (crit) store.stats.crits++;
  if (correct && card.scam) {
    const cats = (card.ai && card.ai.categories) || [];
    if (cats.includes('otp') || cats.includes('upi')) store.cats.otp++;
    if (cats.includes('link') || (card.ai && card.ai.links && card.ai.links.some((l) => l.risk >= 0.5))) store.cats.link++;
  }
  save();
}

export function weightFor(card) {
  const m = store.miss[primaryCategory(card)];
  const rate = m ? (m.miss + 1) / (m.seen + 2) : 0.5;
  return 0.5 + 3 * rate;
}
