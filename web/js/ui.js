// Small DOM helpers and the shared result view. User text is always inserted as text nodes, never as HTML.
import { t } from './i18n.js';
import { store } from './store.js';
import { listenButton } from './speech.js';

export function h(tag, props, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (v == null || v === false) continue;
    if (k === 'class') e.className = v;
    else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
    else if (k === 'style' && typeof v === 'object') Object.assign(e.style, v);
    else if (v === true) e.setAttribute(k, '');
    else e.setAttribute(k, v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    e.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return e;
}
export const $ = (sel, root = document) => root.querySelector(sel);
export const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); return el; };
export const inr = (n) => '₹' + Math.max(0, Math.round(n)).toLocaleString('en-IN');
export const pct = (x) => Math.round(x * 100) + '%';
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
export const shuffle = (a) => { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };

export function toast(msg) {
  const el = h('div', { class: 'toast', role: 'status' }, msg);
  document.body.append(el);
  setTimeout(() => el.remove(), 2200);
}
export function floatText(msg, cls = '') {
  const el = h('div', { class: 'float ' + cls, 'aria-hidden': 'true' }, msg);
  document.body.append(el);
  setTimeout(() => el.remove(), 1200);
}

// ---------- tooltips for highlights (hover on desktop, tap on phones) ----------
let tipEl;
export function initTips() {
  const show = (target) => {
    const text = target.getAttribute('data-tip');
    if (!text) return;
    tipEl = tipEl || h('div', { class: 'tip', role: 'tooltip' });
    tipEl.textContent = text;
    document.body.append(tipEl);
    const r = target.getBoundingClientRect();
    tipEl.style.left = Math.max(8, Math.min(window.innerWidth - 270, r.left)) + 'px';
    tipEl.style.top = (r.bottom + 6) + 'px';
  };
  const hide = () => tipEl && tipEl.remove();
  document.addEventListener('pointerover', (e) => { const x = e.target.closest && e.target.closest('.hl[data-tip]'); if (x) show(x); });
  document.addEventListener('pointerout', (e) => { if (e.target.closest && e.target.closest('.hl[data-tip]')) hide(); });
  document.addEventListener('click', (e) => { const x = e.target.closest && e.target.closest('.hl[data-tip]'); if (x) { show(x); setTimeout(hide, 2500); } });
}

/** Draw the message with highlights. highlights = [{start,end,kind,label}] in characters of the ORIGINAL text. */
export function highlighted(text, highlights, extraClass = '') {
  const box = h('span', { class: 'msgview ' + extraClass });
  let cur = 0;
  for (const hl of (highlights || []).slice().sort((a, b) => a.start - b.start)) {
    if (hl.start < cur || hl.end > text.length || hl.end <= hl.start) continue;
    if (hl.start > cur) box.append(text.slice(cur, hl.start));
    box.append(h('span', { class: 'hl hl-' + hl.kind, 'data-tip': hl.label || '', tabindex: '0' }, text.slice(hl.start, hl.end)));
    cur = hl.end;
  }
  if (cur < text.length) box.append(text.slice(cur));
  return box;
}

export function legend() {
  return h('div', { class: 'legend' },
    h('span', {}, h('i', { style: { background: 'var(--chilli-soft)' } }), t('legend_rule')),
    h('span', {}, h('i', { style: { background: 'var(--rani-soft)' } }), t('legend_link')),
    h('span', {}, h('i', { style: { background: 'var(--marigold-soft)' } }), t('legend_model')));
}

const NS = 'http://www.w3.org/2000/svg';
export function gauge(risk, verdict) {
  const color = verdict === 'scam' ? 'var(--chilli)' : verdict === 'safe' ? 'var(--leaf)' : 'var(--marigold)';
  const len = Math.PI * 70;
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('viewBox', '0 0 170 100'); svg.setAttribute('class', 'gauge'); svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Risk ' + pct(risk));
  const mk = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
  const d = 'M15 85 A70 70 0 0 1 155 85';
  svg.append(mk('path', { d, class: 'track' }));
  const fill = mk('path', { d, class: 'fill', stroke: color, 'stroke-dasharray': len, 'stroke-dashoffset': len });
  svg.append(fill);
  const txt = mk('text', { x: 85, y: 82, 'text-anchor': 'middle' }); txt.textContent = pct(risk);
  svg.append(txt);
  requestAnimationFrame(() => requestAnimationFrame(() => fill.setAttribute('stroke-dashoffset', len * (1 - risk))));
  return svg;
}

export function autopsy(link) {
  const wrap = h('div', { class: 'stack', style: { marginTop: '10px' } });
  wrap.append(h('div', { class: 'small muted', style: { wordBreak: 'break-all' } }, link.url));
  wrap.append(h('div', { class: 'parts' }, link.parts.map((p) => h('span', { class: 'part ' + (p.flag || ''), title: p.note || p.label }, p.text))));
  const notes = link.parts.filter((p) => p.note);
  if (notes.length) wrap.append(h('div', {}, notes.map((p) => h('div', { class: 'partnote' }, (p.flag === 'ok' ? '✅ ' : p.flag === 'bad' ? '🚩 ' : '⚠️ ') + p.label + ': ' + p.note))));
  if (link.official) wrap.append(h('div', { class: 'partnote' }, '✅ ' + link.registered));
  return wrap;
}

function bar(value) {
  return h('div', { class: 'meter' }, h('i', { style: { width: pct(value) } }));
}

/** The full result view used by Scan, Home and the games' reveal. */
export function verdictView(result, text, opts = {}) {
  const v = result.verdict;
  const root = h('div', { class: 'stack', 'aria-live': 'polite' });

  const spoken = [{ text: t('verdict_' + v) + '. ' + t('confidence') + ': ' + t('conf_' + result.confidence) + '.', lang: store.lang },
    { text: summaryLine(result) + ' ' + result.reasons.slice(0, 3).map((r) => r.title + '. ' + r.why).join(' ') + ' ' + result.advice.slice(0, 2).join(' '), lang: 'en' }];
  const listenBtn = listenButton(() => spoken);
  if (store.autoread) setTimeout(() => listenBtn.click(), 500);
  const head = h('div', { class: 'card' },
    h('div', { class: 'verdict' },
      h('div', { style: { textAlign: 'center' } }, gauge(result.risk, v), h('div', { class: 'small muted' }, t('confidence') + ': ' + t('conf_' + result.confidence))),
      h('div', {},
        h('span', { class: 'stamp ' + v }, t('verdict_' + v)), ' ', listenBtn,
        h('p', { style: { marginTop: '12px' } }, summaryLine(result)),
        (result.confidence === 'low' || v === 'suspicious') ? h('div', { class: 'note warn small' }, t('unsure_note')) : null)));
  root.append(head);

  if (opts.showMessage !== false) {
    root.append(h('div', { class: 'card' },
      h('div', { class: 'sender' }, '✉️ ' + (text.length) + ' chars'),
      h('div', { class: 'bubble' }, highlighted(text, result.highlights)), legend()));
  }

  if (result.reasons.length) {
    root.append(h('div', { class: 'card' }, h('h2', {}, t('why_title')),
      h('div', { class: 'stack' }, result.reasons.map((r) => h('div', { class: 'reason' },
        h('h3', {}, r.title),
        r.evidence && r.evidence.length ? h('div', {}, r.evidence.map((e) => h('span', { class: 'ev' }, e.length > 90 ? e.slice(0, 90) + '…' : e))) : null,
        h('div', {}, r.why),
        h('div', { class: 'tipline' }, '💡 ' + r.tip))))));
  }
  if (result.reassurance && result.reassurance.length) {
    root.append(h('div', { class: 'card' }, h('div', { class: 'stack' }, result.reassurance.map((r) => h('div', { class: 'reason' }, h('h3', {}, '✅ ' + r.title), h('div', {}, r.why))))));
  }
  if (result.offline) root.append(h('div', { class: 'note warn small' }, '📴 Offline quick check: this uses the rules and link checks only, without the AI text model or live threat feeds, so it can miss scams. Reconnect for the full analysis.'));
  if (result.source === 'ocr') root.append(h('div', { class: 'note warn small' }, '📷 ' + t('ocr_note')));
  if (result.qr && result.qr.length) {
    root.append(h('div', { class: 'card' }, h('h2', {}, t('qr_title')), h('div', { class: 'stack' }, result.qr.map((q) => qrCard(q)))));
  }
  if (result.links.length) {
    root.append(h('div', { class: 'card' }, h('h2', {}, t('autopsy_title')), result.links.map((l) => autopsy(l))));
  }

  const c = result.components;
  root.append(h('div', { class: 'card' }, h('h2', {}, t('build_title')),
    h('div', { class: 'stack' },
      signal(t('sig_text'), c.text), signal(t('sig_rules'), c.rules), signal(t('sig_links'), c.links),
      h('p', { class: 'small muted' }, 'risk = 1 − (1 − 0.85×text) × (1 − rules) × (1 − 0.95×links)   →   ' + pct(result.risk) + '  ·  ' + result.timing_ms + ' ms'))));

  const up = result.top_words.scam, down = result.top_words.safe;
  if (up.length || down.length) {
    root.append(h('div', { class: 'card' }, h('h2', {}, t('words_title')),
      h('div', { class: 'row' }, up.map((w) => h('span', { class: 'chip up' }, '▲ ' + w.word)), down.map((w) => h('span', { class: 'chip down' }, '▼ ' + w.word)))));
  }

  root.append(h('div', { class: 'card' }, h('h2', {}, t('next_title')),
    h('ul', {}, result.advice.map((a) => h('li', {}, a))),
    h('div', { class: 'row' },
      h('a', { class: 'btn small', href: 'tel:1930' }, '📞 ' + t('helpline')),
      h('a', { class: 'btn small ghost', href: 'https://cybercrime.gov.in', target: '_blank', rel: 'noopener' }, t('report')),
      opts.evidenceCtx && result.verdict !== 'safe' ? h('button', { class: 'btn small scam', type: 'button', onclick: async () => (await import('./evidence.js')).openEvidence(opts.evidenceCtx) }, '📄 ' + t('evidence_btn')) : null)));
  return root;
}

function signal(label, value) {
  return h('div', { class: 'signal' }, h('span', {}, label), bar(value), h('b', {}, pct(value)));
}

function summaryLine(r) {
  const n = r.reasons.length;
  if (r.verdict === 'safe') return n ? 'A couple of small things stood out, but nothing that makes this look like a scam.' : 'No scam signs found in the wording or the links.';
  const top = r.reasons[0];
  return top ? (n + (n === 1 ? ' warning sign found. ' : ' warning signs found. ') + 'Biggest one: ' + top.title.toLowerCase() + '.') : 'The wording looks similar to known scams.';
}

const QR_LABEL = { upi_pay: 'UPI payment QR (sends money OUT)', upi_collect: 'UPI collect request (pulls money from you)', upi_mandate: 'UPI auto-debit mandate', upi_other: 'UPI link', url: 'Web link', other: 'Other QR content' };
function qrCard(q) {
  const f = q.fields || {};
  const rows = [['Payee name', f.pn], ['UPI ID', f.pa], ['Bank / app', f.handle_bank], ['Amount', f.am ? '₹' + f.am : ''], ['Note', f.tn]].filter((r) => r[1]);
  return h('div', { class: 'reason' }, h('h3', {}, (q.risk >= 0.5 ? '🚩 ' : '') + (QR_LABEL[q.type] || q.type)),
    rows.length ? h('div', { class: 'small' }, rows.map((r) => h('div', {}, h('b', {}, r[0] + ': '), String(r[1])))) : h('div', { class: 'ev' }, q.raw.length > 110 ? q.raw.slice(0, 110) + '…' : q.raw),
    q.signals.map((s) => h('div', { class: 'partnote' }, '⚠️ ' + s.title)));
}
