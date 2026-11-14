// Live 1v1 duel over WebSockets. The server owns the clock, the messages and the score; this page only displays them
// and sends taps. If nobody joins within 15 seconds an AI opponent joins automatically. Live duels use the English messages.
import { h, clear, toast, highlighted } from '../ui.js';
import { getConfig } from '../api.js';
import { acct } from '../account.js';
import { shareLink, shareImage } from '../share.js';
import { play } from '../sound.js';
import { markActive, addXP } from '../store.js';

function words(text) { const out = []; const re = /\S+/g; let m; while ((m = re.exec(text))) out.push({ text: m[0], start: m.index, end: m.index + m[0].length }); return out; }
const NAME_KEY = 'scamdojo.name';

export function render(root, params = []) {
  const wanted = (params[0] || '').toUpperCase();
  let ws = null, closed = false, overlay = null, timerId = 0;
  const page = h('section', { class: 'page wrap stack', style: { maxWidth: '640px' } });
  root.append(page);
  const S = { me: null, code: '', names: {}, scores: { A: 0, B: 0 }, text: '', toks: [], tokEls: [], deadline: 0, seconds: 20, locked: true, round: 0, total: 0 };
  const status = h('div', { class: 'small', style: { minHeight: '22px', fontWeight: '700' }, 'aria-live': 'polite' });

  const savedName = () => (acct.user && acct.user.display_name) || localStorage.getItem(NAME_KEY) || '';

  function lobby(error) {
    clear(page);
    const name = h('input', { class: 'field', type: 'text', maxlength: '20', value: savedName(), placeholder: 'Your name', 'aria-label': 'Your name' });
    const code = h('input', { class: 'field', type: 'text', maxlength: '4', value: wanted, placeholder: 'ABCD', style: { textTransform: 'uppercase', letterSpacing: '.2em', textAlign: 'center' }, 'aria-label': 'Room code' });
    const go = (c) => { try { localStorage.setItem(NAME_KEY, name.value); } catch (e) { /* ignore */ } connect(c, name.value || 'Player'); };
    page.append(h('h1', {}, '👥 Live duel'), h('p', { class: 'lead muted' }, 'Race a friend to the red flags in the same message. Whoever taps a flag first claims it. If nobody joins after 2 minutes, an AI opponent steps in.'),
      error ? h('div', { class: 'note warn' }, '⚠️ ' + error) : null,
      h('div', { class: 'card stack' }, h('label', { class: 'lab' }, h('span', {}, 'Your name'), name),
        h('button', { class: 'btn big', type: 'button', onclick: () => go('NEW') }, '➕ Create a room'),
        h('div', { class: 'row' }, h('label', { class: 'lab grow' }, h('span', {}, 'Or join with a code'), code), h('button', { class: 'btn', type: 'button', style: { alignSelf: 'flex-end' }, onclick: () => code.value.trim().length === 4 ? go(code.value.trim()) : toast('Enter the 4-character code') }, 'Join'))),
      h('p', { class: 'small muted' }, 'Live duels use the English version of each message so both players see exactly the same text.'),
      h('a', { class: 'btn ghost', href: '#/duel' }, '🤖 Play against the AI instead'));
    if (wanted && name.value) { /* arrived through an invite link: the name field is ready, one tap to join */ }
  }

  async function connect(code, name) {
    clear(page).append(h('p', {}, 'Connecting…'));
    let cfg;
    try { cfg = await getConfig(); } catch (e) { return unavailable(); }
    if (!cfg.features || !cfg.features.live_duel) return unavailable();
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const base = cfg.ws_port ? proto + '://' + location.hostname + ':' + cfg.ws_port + cfg.ws_path : proto + '://' + location.host + cfg.ws_path;
    let opened = false;
    try { ws = new WebSocket(base + '/' + encodeURIComponent(code) + '?name=' + encodeURIComponent(name)); } catch (e) { return unavailable(); }
    const failTimer = setTimeout(() => { if (!opened) { try { ws.close(); } catch (e) { /* ignore */ } unavailable(); } }, 6000);
    ws.onopen = () => { opened = true; clearTimeout(failTimer); };
    ws.onmessage = (ev) => { try { handle(JSON.parse(ev.data)); } catch (e) { /* ignore malformed */ } };
    ws.onclose = () => { clearTimeout(failTimer); if (!closed && !S.over) { if (!opened) unavailable(); else if (!S.over) { status.textContent = '⚠️ Connection lost.'; } } };
  }

  function unavailable() {
    clear(page).append(h('h1', {}, '👥 Live duel'), h('div', { class: 'note warn' }, '⚠️ Live duels are not available right now (the connection could not be made). You can still play against the AI.'),
      h('div', { class: 'row' }, h('a', { class: 'btn big', href: '#/duel' }, '🤖 Play against the AI'), h('button', { class: 'btn ghost', type: 'button', onclick: () => lobby() }, 'Try again')));
  }

  const send = (o) => { if (ws && ws.readyState === 1) ws.send(JSON.stringify(o)); };

  function handle(m) {
    switch (m.t) {
      case 'joined': S.me = m.you; S.code = m.code; S.names = m.names; S.botWait = m.bot_wait; break;
      case 'waiting': return waitingRoom(m.seconds_left);
      case 'player_joined': S.names = m.names; toast((m.bot ? '🤖 ' : '👤 ') + m.name + ' joined'); break;
      case 'countdown': S.names = m.names; S.total = m.rounds; return countdown(m.seconds);
      case 'round': return startRound(m);
      case 'claimed': S.scores = m.scores; paint(m.start, m.end, m.by); scoreboard(); status.textContent = (m.by === S.me ? '🧑 You found: ' : '🤖/👤 ' + S.names[m.by] + ' found: ') + m.label; if (m.by === S.me) play('crit'); break;
      case 'wrong': S.scores = m.scores; scoreboard(); if (m.by === S.me) { markWrong(m.start, m.end); status.textContent = '❌ Not a red flag (−1)'; play('bad'); } break;
      case 'late': status.textContent = '⏱ Too late: ' + S.names[m.by] + ' got that one first.'; break;
      case 'locked': S.scores = m.scores; scoreboard(); if (m.by === S.me) { S.locked = true; buttons(true); status.textContent = 'Waiting for your opponent…'; } break;
      case 'round_end': return roundEnd(m);
      case 'match_end': return matchEnd(m);
      case 'opponent_left': toast('Your opponent left. 🤖 The AI took their seat.'); break;
      case 'error': return lobby(m.message);
      case 'ping': send({ t: 'ping' }); break;
      default: break;
    }
  }

  // ---------- screens ----------
  function waitingRoom(seconds) {
    clear(page);
    const link = location.origin + location.pathname + '#/duel/live/' + S.code;
    let left = Math.round(seconds || 120);
    const eta = h('b', {}, left + 's');
    clearInterval(timerId); timerId = setInterval(() => { left = Math.max(0, left - 1); eta.textContent = left + 's'; }, 1000);
    page.append(h('h1', {}, '👥 Waiting for a friend'),
      h('div', { class: 'card stack', style: { textAlign: 'center' } }, h('div', { class: 'small muted' }, 'Room code'),
        h('div', { class: 'display', style: { fontSize: '3rem', letterSpacing: '.25em' }, 'aria-label': 'Room code ' + S.code.split('').join(' ') }, S.code),
        h('div', { class: 'row', style: { justifyContent: 'center' } },
          h('button', { class: 'btn small', type: 'button', onclick: () => shareLink({ title: 'ScamDojo duel', text: 'Race me to the red flags! Room ' + S.code, url: link }) }, '📤 Share invite link'),
          h('button', { class: 'btn small ghost', type: 'button', onclick: async () => { try { await navigator.clipboard.writeText(S.code); toast('Code copied'); } catch (e) { toast(S.code); } } }, 'Copy code')),
        h('p', { class: 'small muted' }, 'If nobody joins in ', eta, ', an AI opponent will play instead.')));
  }

  function countdown(seconds) {
    clearInterval(timerId); clear(page);
    let left = Math.ceil(seconds);
    const big = h('div', { class: 'display', style: { fontSize: '4rem', textAlign: 'center' } }, String(left));
    page.append(h('h1', {}, S.names.A + '  vs  ' + S.names.B), h('p', { class: 'muted', style: { textAlign: 'center' } }, 'Get ready…'), big);
    timerId = setInterval(() => { left = Math.max(0, left - 1); big.textContent = String(left || 'Go!'); }, 1000);
  }

  let scoreEl, timerFill, bubble, reveal, doneBtn, cleanBtn, roundChip;
  function matchFrame() {
    clearInterval(timerId); clear(page);
    scoreEl = h('div', { class: 'row', style: { justifyContent: 'space-between' } });
    roundChip = h('span', { class: 'chip' });
    timerFill = h('i', { style: { width: '100%' } });
    bubble = h('div', { class: 'bubble' }); reveal = h('div');
    doneBtn = h('button', { class: 'btn ghost', type: 'button', onclick: () => send({ t: 'done' }) }, '✋ Done');
    cleanBtn = h('button', { class: 'btn legit', type: 'button', onclick: () => send({ t: 'clean' }) }, '✅ Looks clean');
    page.append(h('div', { class: 'card' }, scoreEl, h('div', { class: 'meter timer', style: { marginTop: '10px' } }, timerFill)), bubble, h('div', { class: 'controls' }, cleanBtn, doneBtn), status, reveal);
    scoreboard();
  }
  function scoreboard() {
    if (!scoreEl) return;
    const you = S.me, opp = S.me === 'A' ? 'B' : 'A';
    clear(scoreEl).append(h('span', {}, '🧑 ' + (S.names[you] || 'You') + ' '), h('b', {}, S.scores[you]), roundChip, h('span', {}, (S.names[opp] || 'Opponent') + ' '), h('b', {}, S.scores[opp]));
    if (roundChip) roundChip.textContent = S.round + 1 + '/' + S.total;
  }
  const buttons = (off) => { doneBtn.disabled = off; cleanBtn.disabled = off; };

  function startRound(m) {
    if (!scoreEl || !document.body.contains(scoreEl)) matchFrame();
    S.round = m.index; S.total = m.total; S.scores = m.scores; S.names = m.names; S.text = m.text; S.locked = false; S.seconds = m.seconds; S.deadline = performance.now() + m.seconds * 1000;
    S.toks = words(m.text); clear(reveal); status.textContent = ''; buttons(false);
    S.tokEls = S.toks.map((tk) => h('span', { class: 'tok', role: 'button', tabindex: '0' }, tk.text));
    S.tokEls.forEach((el, i) => el.addEventListener('click', () => { if (!S.locked) send({ t: 'claim', start: S.toks[i].start, end: S.toks[i].end }); }));
    const body = h('div', { class: 'msgview' }); S.tokEls.forEach((el, i) => { body.append(el); if (i < S.tokEls.length - 1) body.append(' '); });
    clear(bubble).append(h('div', { class: 'sender' }, (m.channel === 'sms' ? '✉️ ' : '💬 ') + m.sender), body);
    scoreboard();
    clearInterval(timerId);
    timerId = setInterval(() => { const left = Math.max(0, S.deadline - performance.now()); timerFill.style.width = left / (S.seconds * 1000) * 100 + '%'; timerFill.style.background = left < 4000 ? 'var(--chilli)' : 'var(--marigold)'; }, 100);
  }

  const overlapping = (a, b) => S.toks.map((tk, i) => (tk.start < b && a < tk.end ? i : -1)).filter((i) => i >= 0);
  function paint(start, end, by) {
    overlapping(start, end).forEach((i) => { const el = S.tokEls[i]; const mine = by === S.me; el.style.background = mine ? 'var(--sky)' : 'var(--rani-soft)'; el.style.outline = '2px solid ' + (mine ? 'var(--ink)' : 'var(--rani)'); });
  }
  function markWrong(start, end) { overlapping(start, end).forEach((i) => { S.tokEls[i].style.background = 'var(--chilli-soft)'; S.tokEls[i].style.textDecoration = 'line-through'; }); }

  function roundEnd(m) {
    S.locked = true; S.scores = m.scores; scoreboard(); clearInterval(timerId); timerFill.style.width = '0%'; buttons(true);
    const hl = m.spans.map((s) => ({ start: s.start, end: s.end, kind: s.by === S.me ? 'link' : 'rule', label: (s.by ? S.names[s.by] + ': ' : 'Nobody: ') + s.label }));
    clear(reveal).append(h('div', { class: 'reveal good' }, h('h2', {}, m.truth === 'scam' ? '🚩 This was a scam' : '✅ This message was genuine'), h('p', { class: 'small muted' }, m.reason + '. ' + (m.last ? 'Final scores next.' : 'Next round starting soon…')),
      h('div', { class: 'bubble', style: { margin: '8px 0' } }, highlighted(S.text, hl)),
      m.spans.length ? h('div', { class: 'row' }, m.spans.map((s) => h('span', { class: 'chip' }, (s.by === S.me ? '🧑 ' : s.by ? '🤖/👤 ' : '— ') + s.label))) : null,
      h('p', {}, h('b', {}, 'Lesson: '), m.lesson)));
  }

  function matchEnd(m) {
    S.over = true; clearInterval(timerId); S.scores = m.scores; scoreboard();
    const won = m.winner === S.me, tie = m.winner === 'tie';
    markActive(); addXP(S.scores[S.me] * 2 + (won ? 20 : 0)); play(won ? 'win' : 'bad');
    const opp = S.me === 'A' ? 'B' : 'A';
    overlay = h('div', { class: 'overlay', role: 'dialog', 'aria-modal': 'true' }, h('div', { class: 'card stack' },
      h('h2', {}, won ? '🏆 You won the duel!' : tie ? '🤝 A tie' : '😤 ' + S.names[opp] + ' wins'),
      h('p', { class: 'display', style: { fontSize: '2rem', margin: 0 } }, S.names[S.me] + ' ' + S.scores[S.me] + ' – ' + S.scores[opp] + ' ' + S.names[opp]),
      h('div', { class: 'row' }, h('button', { class: 'btn small ghost', type: 'button', onclick: () => shareImage({ title: 'Live red-flag duel', big: S.scores[S.me] + '–' + S.scores[opp], lines: [won ? 'I won!' : tie ? 'A tie' : 'Rematch soon.', 'vs ' + S.names[opp]], accent: '#D6247F' }) }, '📤 Share'),
        h('button', { class: 'btn', type: 'button', onclick: () => { overlay.remove(); location.hash = '#/duel/live'; location.reload(); } }, 'New match'), h('a', { class: 'btn ghost', href: '#/duel' }, '🤖 Play the AI'))));
    document.body.append(overlay);
  }

  lobby();
  return () => { closed = true; clearInterval(timerId); try { if (ws) ws.close(); } catch (e) { /* ignore */ } if (overlay) overlay.remove(); };
}
