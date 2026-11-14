// OFFLINE QUICK CHECK. A compact browser version of the engine for when the server cannot be reached: the same rules, link checks and
// UPI-QR logic (loaded from data/offline_pack.json, which is exported from the Python definitions), but NO machine-learning text
// model and no live threat feeds. It is deliberately labelled "limited" and always reports low confidence.
let PACK = null, COMPILED = null;

async function load() {
  if (COMPILED) return;
  PACK = await (await fetch('/data/offline_pack.json')).json();
  const rx = (p, f = 'gis') => { try { return new RegExp(p, f); } catch (e) { return null; } };
  COMPILED = {
    rules: PACK.rules.map((r) => ({ ...r, rx: r.patterns.map((p) => rx(p)).filter(Boolean) })),
    safe: PACK.safe_rules.map((r) => ({ ...r, rx: r.patterns.map((p) => rx(p, 'is')).filter(Boolean) })),
    neg: rx(PACK.neg_ctx, 'i'), benign: rx(PACK.benign_ctx, 'i'),
    url: rx('(?:https?://|www\\.)[^\\s<>"\']+|(?<![\\w@.-])(?:bit\\.ly|tinyurl\\.com|t\\.co|goo\\.gl|rb\\.gy|cutt\\.ly|is\\.gd|tiny\\.cc|shorturl\\.at|ow\\.ly|t\\.ly|wa\\.me|t\\.me)/[^\\s<>"\']+|(?<![\\w@.-])(?:[a-z0-9](?:[a-z0-9\\-]{0,61}[a-z0-9])?\\.)+(?:' + PACK.tld_list + ')(?![\\w@-])(?:/[^\\s<>"\']*)?', 'gi'),
    official: new Set(Object.values(PACK.brands).flatMap((b) => b.official)),
    kwBrand: Object.fromEntries(Object.entries(PACK.brands).flatMap(([name, b]) => b.keywords.map((k) => [k, name]))),
    multi: new Set(PACK.multi_suffix), short: new Set(PACK.shorteners), risky: new Set(PACK.risky_tlds), free: PACK.free_hosting,
  };
}

const HOMO = { 'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', 'і': 'i', 'ѕ': 's', 'ο': 'o', 'ν': 'v', 'ι': 'i', 'α': 'a', 'ε': 'e', 'ρ': 'p' };
function normalize(raw) {
  const flags = { zero_width: 0, homoglyph: 0, spaced: 0 };
  let out = '';
  for (const ch of raw) {
    if (/[\u200b-\u200f\u2060\ufeff\u00ad]/.test(ch)) { flags.zero_width++; continue; }
    let c = ch.normalize('NFKC').toLowerCase();
    if (HOMO[c]) { c = HOMO[c]; flags.homoglyph++; }
    out += c;
  }
  const collapsed = out.replace(/(?<![a-z0-9])(?:[a-z][ .\-_*]){2,}[a-z](?![a-z0-9])/g, (m) => { flags.spaced++; return m.replace(/[ .\-_*]/g, ''); });
  return { text: out, matchText: collapsed, flags, aligned: out.length === raw.length };
}

// ---------- links ----------
function damerau(a, b) {
  const d = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 0; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) {
    const c = a[i - 1] === b[j - 1] ? 0 : 1;
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c);
    if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
  }
  return d[a.length][b.length];
}
const skeleton = (s) => s.toLowerCase().replace(/[-_]/g, '').replace(/rn/g, 'm').replace(/vv/g, 'w').replace(/cl/g, 'd').replace(/[01345 7]/g, (c) => ({ 0: 'o', 1: 'l', 3: 'e', 5: 's', 4: 'a', 7: 't' }[c] || c));

function splitHost(host) {
  const l = host.split('.');
  if (l.length >= 3 && COMPILED.multi.has(l.slice(-2).join('.'))) return [l.slice(0, -3).join('.'), l[l.length - 3], l.slice(-2).join('.')];
  if (l.length >= 2) return [l.slice(0, -2).join('.'), l[l.length - 2], l[l.length - 1]];
  return ['', host, ''];
}

function impersonation(sub, name) {
  const tokens = name.split(/[-_.0-9]+/).filter(Boolean), subTokens = sub.split(/[-_.0-9]+/).filter(Boolean), kw = COMPILED.kwBrand;
  for (const k of Object.keys(kw)) {
    if (k.length >= 6 && name.includes(k)) return [kw[k], 'brand_in_domain'];
    if (tokens.includes(k) || (k.length >= 4 && (name.startsWith(k) || name.endsWith(k)))) return [kw[k], 'brand_in_domain'];
  }
  for (const k of Object.keys(kw)) if (subTokens.includes(k) || (k.length >= 5 && sub.includes(k))) return [kw[k], 'brand_in_subdomain'];
  for (const k of Object.keys(kw)) {
    if (k.length < 5) continue;
    for (const t of [name, ...tokens]) {
      if (t.length < 4 || t === k) continue;
      const lim = k.length >= 8 ? 2 : 1;
      if (damerau(skeleton(t), skeleton(k)) <= lim && Math.abs(t.length - k.length) <= 2) return [kw[k], 'lookalike'];
    }
    if (skeleton(name).includes(skeleton(k)) && !name.includes(k)) return [kw[k], 'lookalike'];
  }
  return null;
}

function analyzeUrl(raw) {
  const hasScheme = /^[a-z]+:\/\//i.test(raw);
  let u;
  try { u = new URL(hasScheme ? raw : 'http://' + raw); } catch (e) { return null; }
  const host = u.hostname.toLowerCase(), isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(host);
  const [sub, name, suffix] = isIp ? ['', host, ''] : splitHost(host), registered = isIp ? host : (suffix ? name + '.' + suffix : host);
  const path = u.pathname + u.search, parts = [];
  const sig = [], add = (id, label, weight, detail, part) => sig.push({ id, label, weight, detail, part });
  if (hasScheme) parts.push({ label: 'scheme', text: u.protocol + '//', flag: u.protocol === 'http:' ? 'warn' : null, note: u.protocol === 'http:' ? 'No encryption (http)' : null });
  const official = COMPILED.official.has(registered) || PACK.trusted_suffixes.some((s) => suffix === s || host.endsWith('.' + s));
  if (official) {
    if (sub) parts.push({ label: 'subdomain', text: sub + '.', flag: null });
    parts.push({ label: 'domain', text: name, flag: 'ok', note: 'Official domain' }, { label: 'suffix', text: '.' + suffix, flag: 'ok' });
    if (path && path !== '/') parts.push({ label: 'path', text: path, flag: null });
    return { url: raw, host, registered, risk: 0.03, official: true, brand: null, signals: [], parts, verdict: 'official' };
  }
  let brand = null;
  if (isIp) add('ip_host', 'Uses a raw IP address', 0.6, 'Real services use names, not numbers.', 'domain');
  if (host.includes('xn--')) add('punycode', 'Uses disguised (punycode) characters', 0.55, 'Foreign look-alike letters can spoof real names.', 'domain');
  if (u.username) add('at_sign', 'Has an @ in the address', 0.6, 'Everything before the @ is ignored by the browser.', 'domain');
  if (COMPILED.short.has(registered)) add('shortener', 'Shortened link hides the destination', 0.45, 'You cannot see where it goes before you tap.', 'domain');
  else if (!isIp) {
    const imp = impersonation(sub, name);
    if (imp) {
      brand = imp[0];
      const real = PACK.brands[imp[0]].official[0];
      if (imp[1] === 'brand_in_domain') add('brand_in_domain', 'Uses the ' + imp[0] + ' name but is not ' + real, 0.8, 'The real ' + imp[0] + ' website is ' + real + '.', 'domain');
      else if (imp[1] === 'brand_in_subdomain') add('brand_in_subdomain', 'Puts ' + imp[0] + ' in front to look official', 0.8, 'The real owner of this link is ' + registered + '.', 'subdomain');
      else add('lookalike', 'Look-alike spelling of ' + imp[0], 0.85, 'Letters were swapped to imitate ' + real + '.', 'domain');
    }
    if (COMPILED.risky.has(suffix)) add('risky_tld', 'Unusual ending .' + suffix, 0.3, 'Cheap endings are common in scam sites.', 'suffix');
    if (COMPILED.free.some((f) => registered === f || host.endsWith('.' + f))) add('free_hosting', 'Hosted on a free site builder', 0.4, 'Anyone can create a page here in minutes.', 'domain');
    if ((host.match(/-/g) || []).length >= 3) add('many_hyphens', 'Many hyphens in the name', 0.25, 'Typical of fake sites.', 'domain');
    if (sub && sub.split('.').length >= 3) add('deep_subdomain', 'Many sub-domains', 0.25, 'Buries the real owner.', 'subdomain');
    if (/\d{3,}/.test(name)) add('digits_name', 'Lots of digits in the name', 0.15, 'Often a throw-away site.', 'domain');
  }
  if (/\.apk(\?|$)/i.test(path)) add('apk', 'Downloads an app file (.apk)', 0.75, 'Installing apps from links can hand over your phone.', 'path');
  const pw = PACK.path_words.find((w) => path.toLowerCase().includes(w));
  if (pw && sig.length) add('path_words', 'Asks you to ' + pw, 0.2, 'Words like login/verify/claim are used as bait.', 'path');
  if (u.protocol === 'http:' && sig.length) add('no_tls', 'Not encrypted (http)', 0.1, 'Real banks and shops use https.', 'scheme');
  let miss = 1; sig.forEach((s) => { miss *= 1 - s.weight; });
  const risk = sig.length ? Math.min(0.98, 1 - miss) : 0.12;
  const by = {}; sig.forEach((s) => (by[s.part] = by[s.part] || []).push(s));
  if (sub) parts.push({ label: 'subdomain', text: sub + '.', flag: by.subdomain ? 'warn' : null, note: by.subdomain ? by.subdomain[0].label : null });
  parts.push({ label: 'domain', text: name, flag: by.domain ? (Math.max(...by.domain.map((s) => s.weight)) >= 0.6 ? 'bad' : 'warn') : null, note: by.domain ? by.domain[0].label : null });
  if (suffix) parts.push({ label: 'suffix', text: '.' + suffix, flag: by.suffix ? 'warn' : null, note: by.suffix ? by.suffix[0].label : null });
  if (path && path !== '/') parts.push({ label: 'path', text: path, flag: by.path ? 'warn' : null, note: by.path ? by.path[0].label : null });
  return { url: raw, host, registered, risk: +risk.toFixed(3), official: false, brand, signals: sig, parts, verdict: risk >= 0.65 ? 'dangerous' : risk >= 0.3 ? 'suspicious' : 'unknown' };
}

// ---------- UPI QR ----------
function analyzeUpi(payload, intent, context) {
  if (intent === 'unknown' && /\b(?:receive|received|refund|cashback|credit(?:ed)?|reward|prize|won|winning|bonus|reversal|collect)\b/i.test(context || '')) intent = 'receive';
  if (!/^upi:\/\//i.test(payload.trim())) return { type: /^(https?:\/\/|www\.)/i.test(payload.trim()) ? 'url' : 'other', raw: payload.slice(0, 300), signals: [], risk: 0, intent };
  const url = new URL(payload.trim().replace(/^upi:\/\//i, 'https://upi.invalid/')), q = Object.fromEntries([...url.searchParams].map(([k, v]) => [k.toLowerCase(), v]));
  const kind = url.pathname.replace(/\//g, '').toLowerCase() || 'other', sig = [];
  const add = (id, title, weight) => sig.push({ id, title, weight });
  if (kind === 'collect' || kind === 'mandate') add('upi_collect_qr', kind === 'collect' ? 'This QR asks to PULL money from your account' : 'This QR sets up an auto-debit mandate', 0.9);
  else if (kind === 'pay') {
    if (intent === 'receive') add('upi_pay_qr_receive', 'You expect to RECEIVE money, but this QR sends it OUT', 0.95);
    else if (intent === 'unknown') add('upi_pay_qr', 'This is a payment QR: only scan it to pay someone', 0.55);
  }
  if (q.tn && /refund|reward|cashback|prize|lottery|lucky|kyc|verify|bonus|gift|claim|winning|reversal/i.test(q.tn)) add('upi_note_bait', 'The payment note uses bait words', 0.5);
  let miss = 1; sig.forEach((s) => { miss *= 1 - s.weight; });
  return { type: 'upi_' + (['pay', 'collect', 'mandate'].includes(kind) ? kind : 'other'), raw: payload.slice(0, 300), fields: { pa: q.pa || '', pn: q.pn || '', am: q.am ? parseFloat(q.am) : null, tn: q.tn || '' }, signals: sig, risk: +(1 - miss).toFixed(3), intent };
}

// ---------- entities (basic) ----------
function entities(text) {
  const uniq = (a) => [...new Set(a)];
  return { phones: uniq((text.match(/(?<![\d@])(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)/g) || []).map((p) => '+91 ' + p.replace(/\D/g, '').slice(-10))),
    upi_ids: uniq(text.match(/(?<![\w.@-])[a-z0-9][a-z0-9._-]{1,48}@[a-z][a-z0-9]{1,22}(?![\w.@-]|\.[a-z])/gi) || []),
    urls: [], upi_links: uniq(text.match(/upi:\/\/[^\s<>"']+/gi) || []), emails: [], amounts: uniq(text.match(/(?:₹|\brs\.?|\binr)\s?\d[\d,]*(?:\.\d+)?/gi) || []), dates: [], times: [], ifsc: [], long_numbers: [] };
}

const ADVICE = {
  scam: ['Do not tap links, call numbers or share any code from this message.', 'Verify using the official app or the phone number printed on your card or bill.', 'If money or details were already shared: call your bank immediately, then the National Cyber Crime Helpline 1930.', 'Report it at cybercrime.gov.in.'],
  suspicious: ["Don't act on it yet. Check the claim in the official app or website (typed by you, not from the message).", 'Not sure? Ask a family member or call 1930 for guidance.'],
  safe: ['Nothing alarming was found by the quick check, but stay careful with any message that asks for money, codes or urgent action.'],
};

/** Same result shape as /api/scan, so the normal result screen can show it. */
export async function offlineScan({ text = '', intent = 'unknown', qr = [] }) {
  await load();
  const t0 = performance.now();
  text = text.slice(0, 5000);
  const n = normalize(text), hl = [], hits = [], safeHits = [];
  for (const r of COMPILED.rules) {
    const spans = [];
    for (const re of r.rx) for (const m of n.matchText.matchAll(re)) {
      if (!m[0]) continue;
      if (r.neg && COMPILED.neg && COMPILED.neg.test(n.matchText.slice(Math.max(0, m.index - 70), m.index))) continue;
      if (r.ctx_skip && COMPILED.benign && COMPILED.benign.test(n.matchText.slice(Math.max(0, m.index - 80), m.index + m[0].length + 40))) continue;
      spans.push([m.index, m.index + m[0].length, m[0]]);
      if (spans.length >= 3) break;
    }
    if (spans.length) hits.push({ ...r, spans });
  }
  for (const r of COMPILED.safe) if (r.rx.some((re) => re.test(n.matchText))) safeHits.push(r);
  let miss = 1; hits.forEach((h) => { miss *= 1 - h.weight * 0.95; });
  const rScore = Math.min(0.98, 1 - miss);

  const links = [];
  for (const m of n.matchText.matchAll(COMPILED.url)) {
    const url = m[0].replace(/[.,;:)\]}!?'"]+$/, '');
    const res = url.toLowerCase().startsWith('upi://') ? null : analyzeUrl(url);
    if (res) { res.span = n.aligned && n.text === n.matchText ? [m.index, m.index + url.length] : null; links.push(res); }
  }
  const upiPayloads = [...(text.match(/upi:\/\/[^\s<>"']+/gi) || []), ...qr.filter((p) => typeof p === 'string' && p.trim())];
  const qrItems = upiPayloads.map((p) => analyzeUpi(p, intent, text));
  qrItems.filter((i) => i.type === 'url').forEach((i) => { const r = analyzeUrl(i.raw); if (r) { r.span = null; links.push(r); } });
  let uScore = Math.max(0, ...links.map((l) => l.risk)); if (links.length && links.every((l) => l.official)) uScore = 0;
  const qScore = Math.max(0, ...qrItems.map((i) => i.risk));

  let risk = 1 - (1 - rScore) * (1 - 0.95 * uScore) * (1 - 0.95 * qScore);
  const strong = hits.some((h) => h.weight >= 0.7) || uScore >= 0.7 || qScore >= 0.7;
  if (safeHits.length && !strong) risk *= 1 - Math.min(0.5, safeHits.reduce((a, s) => a + s.weight, 0));
  risk = +Math.max(0, Math.min(0.99, risk)).toFixed(3);
  const verdict = risk >= 0.65 ? 'scam' : risk < 0.35 ? 'safe' : 'suspicious';

  if (n.aligned && n.text === n.matchText) {
    hits.forEach((h) => h.spans.forEach(([a, b]) => hl.push({ start: a, end: b, kind: 'rule', id: h.id, label: h.title })));
    links.forEach((l) => { if (l.span) hl.push({ start: l.span[0], end: l.span[1], kind: 'link', id: 'link', label: l.official ? 'Official link' : 'Link looks ' + l.verdict }); });
    hl.sort((a, b) => a.start - b.start);
  }
  const clean = []; for (const h of hl) if (!clean.length || h.start >= clean[clean.length - 1].end) clean.push(h);

  const reasons = hits.map((h) => ({ id: h.id, category: h.category, title: h.title, why: h.why, tip: h.tip, weight: h.weight, source: 'rule', evidence: h.spans.slice(0, 2).map((s) => s[2]) }));
  links.forEach((l) => l.signals.forEach((s) => { if (s.weight >= 0.3) reasons.push({ id: s.id, category: 'link', title: s.label, why: s.detail, tip: 'Open the official app or type the website yourself.', weight: s.weight, source: 'link', evidence: [l.url] }); }));
  qrItems.forEach((i) => i.signals.forEach((s) => { if (s.weight >= 0.3) reasons.push({ id: s.id, category: 'upi', title: s.title, why: 'Scanning a payment QR and entering your PIN pays the person named in it.', tip: 'Never scan a QR code or enter your UPI PIN to receive money.', weight: s.weight, source: 'qr', evidence: [i.raw.slice(0, 120)] }); }));
  reasons.sort((a, b) => b.weight - a.weight);
  const ents = entities(text); links.forEach((l) => ents.urls.push(l.url));
  const advice = ADVICE[verdict].slice(); if (qScore >= 0.5) advice.unshift('Do not scan or approve it. Receiving money never needs a QR scan or your UPI PIN.');
  return { offline: true, risk, verdict, confidence: 'low', confidence_score: 0.2, components: { text: 0, rules: +rScore.toFixed(3), links: +uScore.toFixed(3), upi: +qScore.toFixed(3) },
    highlights: clean, reasons: reasons.slice(0, 8), links, qr: qrItems.map((i) => ({ type: i.type, raw: i.raw, fields: i.fields, risk: i.risk, intent: i.intent, signals: i.signals })),
    reassurance: safeHits.map((s) => ({ id: s.id, title: s.title, why: s.why })), top_words: { scam: [], safe: [] }, normalization: n.flags,
    categories: [...new Set(reasons.map((r) => r.category).filter((c) => !['link', 'urgency'].includes(c)))], advice, entities: ents, entity_counts: {}, source: 'text', text_used: null,
    model_version: 'offline-quick-check', timing_ms: +(performance.now() - t0).toFixed(2), length: text.length };
}

export const isNetworkError = (e) => !navigator.onLine || e instanceof TypeError || /fetch|network|load failed/i.test(String(e && e.message));
