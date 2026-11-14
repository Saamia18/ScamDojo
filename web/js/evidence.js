// The 1930 / cybercrime.gov.in evidence packet: a short form, then a copy-ready brief and a printable report.
import { h, clear, toast } from './ui.js';
import { buildEvidence } from './api.js';

function download(name, text, type) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name;
  document.body.append(a); a.click(); a.remove();
}
function printHtml(html) {
  const f = document.createElement('iframe');
  f.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0';
  f.onload = () => { try { f.contentWindow.focus(); f.contentWindow.print(); } finally { setTimeout(() => f.remove(), 1500); } };
  f.srcdoc = html;
  document.body.append(f);
}

/** ctx = { text, source, intent, qr }. prefill = values for the form (used by the Protect page). */
export function openEvidence(ctx, prefill = {}) {
  const box = h('div', { class: 'card stack' });
  const overlay = h('div', { class: 'overlay', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Evidence packet' }, box);
  document.body.append(overlay);
  const close = () => { overlay.remove(); window.removeEventListener('hashchange', close); };
  window.addEventListener('hashchange', close);  // leaving the page closes the dialog
  const field = (label, el) => h('label', { class: 'lab' }, h('span', { class: 'small muted' }, label), el);
  const check = (label, checked) => { const c = h('input', { type: 'checkbox' }); c.checked = !!checked; return { c, el: h('label', { class: 'row' }, c, h('span', {}, label)) }; };

  function form() {
    const amount = h('input', { class: 'field', type: 'text', inputmode: 'decimal', placeholder: 'e.g. 5000', value: prefill.amount || '' });
    const when = h('input', { class: 'field', type: 'text', placeholder: 'e.g. 12 Nov, 9:45 pm', value: prefill.when || '' });
    const payment = h('select', { class: 'field' }, [['', 'Not paid / not sure'], ['upi', 'UPI'], ['card', 'Debit / credit card'], ['netbanking', 'Net banking'], ['cash', 'Cash or other']].map(([v, l]) => h('option', { value: v }, l)));
    payment.value = prefill.payment || '';
    const txn = h('input', { class: 'field', type: 'text', maxlength: '40', placeholder: 'Transaction ID / UTR (if any)' });
    const note = h('textarea', { class: 'field', rows: '3', maxlength: '600', placeholder: 'Anything else that happened' });
    note.value = prefill.note || '';
    const text = h('textarea', { class: 'field', rows: '4', maxlength: '5000', placeholder: 'Paste the scam message here (optional)' });
    text.value = ctx.text || '';
    const lost = check('I lost money', prefill.lost_money), otp = check('I shared an OTP or PIN'), app = check('I installed an app from a link'), link = check('I opened a link');
    const err = h('div', { class: 'note warn hide', role: 'alert' });
    const go = h('button', { class: 'btn', type: 'submit' }, 'Create packet');
    const f = h('form', { class: 'stack' },
      h('h2', {}, '📄 ' + 'Evidence packet for 1930'), h('p', { class: 'small muted' }, 'Everything here is optional. The packet is built on request and is not stored. Do not include card numbers or passwords.'),
      ctx.text ? null : field('Scam message', text),
      h('div', { class: 'grid cols-2' }, field('Amount lost (₹)', amount), field('When it happened', when), field('How you paid', payment), field('Transaction ID / UTR', txn)),
      h('div', { class: 'stack' }, lost.el, otp.el, app.el, link.el), field('Notes', note), err,
      h('div', { class: 'row' }, go, h('button', { class: 'btn ghost', type: 'button', onclick: close }, 'Cancel')));
    f.addEventListener('submit', async (e) => {
      e.preventDefault(); err.classList.add('hide'); go.disabled = true; go.textContent = 'Working…';
      try {
        const msg = ctx.text || text.value;
        if (!msg.trim() && !(ctx.qr && ctx.qr.length)) throw new Error('Paste the message first, or scan a QR code.');
        const pk = await buildEvidence({ text: msg, source: ctx.source || 'text', intent: ctx.intent || 'unknown', qr: ctx.qr || [],
          details: { amount: amount.value, when: when.value, payment: payment.value, txn_id: txn.value, note: note.value, lost_money: lost.c.checked, shared_otp: otp.c.checked, installed_app: app.c.checked, clicked_link: link.c.checked } });
        result(pk);
      } catch (ex) { err.textContent = '⚠️ ' + ex.message; err.classList.remove('hide'); go.disabled = false; go.textContent = 'Create packet'; }
    });
    clear(box).append(f);
  }

  function result(pk) {
    const e = pk.entities, chips = [];
    [['📞', e.phones], ['💳', e.upi_ids], ['🔗', e.urls], ['🔲', e.upi_links], ['✉️', e.emails]].forEach(([i, list]) => (list || []).forEach((x) => chips.push(h('span', { class: 'chip' }, i + ' ' + (x.length > 38 ? x.slice(0, 38) + '…' : x)))));
    const ta = h('textarea', { class: 'field', rows: '12', readonly: true, 'aria-label': 'Complaint brief', style: { fontFamily: 'ui-monospace,Menlo,Consolas,monospace', fontSize: '.82rem' } });
    ta.value = pk.brief_text;
    const day = new Date().toISOString().slice(0, 10);
    clear(box).append(h('h2', {}, '✅ Your evidence packet'),
      h('div', { class: 'note' }, h('b', {}, 'Suggested category: '), pk.summary.suggested_category, pk.summary.also_matches.length ? h('div', { class: 'small' }, 'Also matches: ' + pk.summary.also_matches.join('; ')) : null),
      chips.length ? h('div', { class: 'row' }, chips) : h('p', { class: 'small muted' }, 'No phone numbers, UPI IDs or links were found in the message.'), ta,
      h('div', { class: 'row' },
        h('button', { class: 'btn small', type: 'button', onclick: async () => { try { await navigator.clipboard.writeText(pk.brief_text); toast('Copied'); } catch (x) { ta.select(); toast('Press Ctrl+C to copy'); } } }, '📋 Copy text'),
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => download('scamdojo-evidence-' + day + '.html', pk.html, 'text/html') }, '⬇️ Download report'),
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => printHtml(pk.html) }, '🖨️ Print / save as PDF')),
      h('div', { class: 'row' }, h('a', { class: 'btn', href: 'tel:1930' }, '📞 Call 1930'), h('a', { class: 'btn ghost', href: 'https://cybercrime.gov.in', target: '_blank', rel: 'noopener' }, 'Open cybercrime.gov.in')),
      h('p', { class: 'small muted' }, pk.disclaimer), h('button', { class: 'btn small ghost', type: 'button', onclick: close }, 'Close'));
  }

  form();
  overlay.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
}
