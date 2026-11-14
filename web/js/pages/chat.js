// Dojo Bot: a small rule-based helper (no LLM). Answers common questions, and checks any long message you paste.
import { h, clear } from '../ui.js';
import { analyze } from '../api.js';
import { t } from '../i18n.js';

const FAQ = [
  [/(already|got scammed|lost money|fraud happened|money (is )?gone|paid)/i, 'Act fast: call your bank to freeze the account or card, then call the National Cyber Crime Helpline 1930 and file a report at cybercrime.gov.in. Speed matters, so do this first.'],
  [/\botp\b|\bpin\b|\bcvv\b/i, 'Never share an OTP, UPI PIN, CVV or password with anyone, including people who say they are from your bank. Banks never ask for them.'],
  [/\bupi\b|collect request|qr/i, 'You never need to enter a PIN or approve a request to RECEIVE money. A PIN or an approval only ever sends money out.'],
  [/\bkyc\b|\bpan\b|aadhaar/i, 'Real KYC updates happen in your bank\'s own app or at the branch. A KYC link or a call from an unknown number is a scam.'],
  [/helpline|1930|report|complaint/i, 'Call 1930 (National Cyber Crime Helpline) or report at cybercrime.gov.in. Keep screenshots of the messages.'],
  [/job|work from home|earn/i, 'Real employers never charge a fee to hire you, and nobody pays you to like videos or rate hotels. Treat those offers as scams.'],
  [/parcel|courier|customs/i, 'Track parcels only in the shop\'s app or on the courier\'s official site. Customs never takes payment on a personal UPI number.'],
  [/hello|hi\b|help|hey/i, 'Hi! Ask me about OTPs, KYC, UPI, parcels or jobs, or paste a suspicious message and I will check it.'],
];

export function mount(root) {
  const log = h('div', { class: 'log' }, bot('Hi, I am Dojo Bot. Ask a scam question or paste a suspicious message.'));
  const input = h('input', { type: 'text', placeholder: 'Ask or paste a message…', 'aria-label': 'Message to Dojo Bot', maxlength: '2000' });
  const panel = h('div', { class: 'chat hide', role: 'dialog', 'aria-label': 'Dojo Bot' },
    h('header', {}, h('span', {}, '🥋 Dojo Bot'), h('button', { class: 'pill', type: 'button', onclick: () => panel.classList.add('hide'), 'aria-label': 'Close' }, '×')),
    log, h('form', { onsubmit: send }, input, h('button', { class: 'btn small', type: 'submit' }, '➤')));
  const fab = h('button', { class: 'fab', type: 'button', 'aria-label': 'Open Dojo Bot', onclick: () => { panel.classList.toggle('hide'); input.focus(); } }, '💬');
  root.append(panel, fab);

  function push(el) { log.append(el); log.scrollTop = log.scrollHeight; }
  async function send(e) {
    e.preventDefault();
    const q = input.value.trim(); if (!q) return;
    input.value = '';
    push(h('div', { class: 'msgb me' }, q));
    if (q.length > 45) {
      try {
        const r = await analyze(q);
        const top = r.reasons.slice(0, 2).map((x) => x.title).join('; ');
        push(bot((r.verdict === 'scam' ? '🚩 Likely scam' : r.verdict === 'suspicious' ? '⚠️ Be careful' : '✅ Looks safe') + ' (' + Math.round(r.risk * 100) + '% risk).' + (top ? ' ' + top + '.' : '') + ' ' + r.advice[0]));
      } catch (err) { push(bot('Sorry, I could not check that: ' + err.message)); }
      return;
    }
    const hit = FAQ.find(([rx]) => rx.test(q));
    push(bot(hit ? hit[1] : 'I do not know that one yet. If you have a message, paste the full text and I will check it. For fraud, call 1930.'));
  }
}
const bot = (text) => h('div', { class: 'msgb bot' }, text);
