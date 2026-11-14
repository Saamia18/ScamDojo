// The scanner: a phone with an editable message, plus screenshot (OCR) and QR input. Used on Home and on the Scan page.
import { h, clear, verdictView, highlighted, legend } from './ui.js';
import { scan, getSamples } from './api.js';
import { t } from './i18n.js';
import { store, markActive } from './store.js';
import { decodeQR, readText, scanWithCamera } from './vision.js';
import { offlineScan, isNetworkError } from './offline.js';

export function buildScanner(outEl, { initial = '' } = {}) {
  const state = { source: 'text', qr: [], intent: 'unknown' };
  const ta = h('textarea', { class: 'msg', placeholder: t('paste_ph'), 'aria-label': t('paste_ph'), maxlength: '5000' });
  ta.value = initial;
  const bubble = h('div', { class: 'bubble' }, ta);
  const legendBox = h('div', { class: 'hide' }, legend());
  const phone = h('div', { class: 'phone' }, h('div', { class: 'notch' }), h('div', { class: 'screen' }, h('div', { class: 'sender' }, '📱 +91 ··· ·····'), bubble, legendBox));
  const btn = h('button', { class: 'btn big', type: 'button' }, t('check'));
  const edit = h('button', { class: 'btn ghost small hide', type: 'button' }, '✏️');
  const chips = h('div', { class: 'row', style: { marginTop: '12px', justifyContent: 'center' } });
  const status = h('div', { class: 'readstat', 'aria-live': 'polite' });
  const intentBox = h('div', { class: 'intent hide' });
  let lastText = '';

  // ---------- image input: file, drop, paste, camera ----------
  const file = h('input', { type: 'file', accept: 'image/*', 'aria-label': t('drop_title') });
  const drop = h('label', { class: 'drop', tabindex: '0' }, h('div', { style: { fontSize: '1.8rem' } }, '📷'), h('b', {}, t('drop_title')), h('div', { class: 'small muted' }, t('drop_sub')), h('div', { class: 'small' }, '🔒 ' + t('drop_private')), file);
  file.addEventListener('change', () => { if (file.files[0]) handleImage(file.files[0]); file.value = ''; });
  drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); file.click(); } });
  ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', (e) => { const f = e.dataTransfer && e.dataTransfer.files[0]; if (f && f.type.startsWith('image/')) handleImage(f); });
  const onPaste = (e) => {
    const item = [...((e.clipboardData && e.clipboardData.items) || [])].find((i) => i.type.startsWith('image/'));
    if (item) { e.preventDefault(); handleImage(item.getAsFile()); }
  };
  document.addEventListener('paste', onPaste);
  new MutationObserver((_, obs) => { if (!document.body.contains(phone)) { document.removeEventListener('paste', onPaste); obs.disconnect(); } }).observe(document.body, { childList: true, subtree: true });

  const camBtn = h('button', { class: 'btn small ghost', type: 'button' }, '🎥 ' + t('camera'));
  const camBox = h('div', { class: 'cam hide' });
  let cam = null;
  async function stopCam() { if (cam) { cam.stop(); cam = null; } camBox.classList.add('hide'); clear(camBox); camBtn.textContent = '🎥 ' + t('camera'); }
  camBtn.addEventListener('click', async () => {
    if (cam) return stopCam();
    const video = h('video', { muted: true, playsinline: true, 'aria-label': 'Camera preview' });
    clear(camBox).append(video); camBox.classList.remove('hide'); camBtn.textContent = '⏹ ' + t('stop_camera');
    cam = await scanWithCamera(video, (payload) => { stopCam(); useQR([payload]); run(); }, (err) => { stopCam(); status.textContent = '⚠️ ' + err.message; });
  });

  function useQR(codes) {
    state.qr = codes;
    clear(intentBox).append(h('div', { class: 'small', style: { fontWeight: '700', marginBottom: '6px' } }, '🔲 ' + t('qr_found') + ' · ' + t('intent_q')),
      h('div', { class: 'row', style: { justifyContent: 'center' } }, ...[['receive', 'intent_receive'], ['pay', 'intent_pay'], ['unknown', 'intent_unknown']].map(([v, k]) =>
        h('button', { class: 'chip', type: 'button', 'aria-pressed': String(state.intent === v), onclick: () => { state.intent = v; useQR(state.qr); run(); } }, (state.intent === v ? '✓ ' : '') + t(k)))));
    intentBox.classList.remove('hide');
  }

  async function handleImage(f) {
    state.qr = []; state.intent = 'unknown'; intentBox.classList.add('hide');
    try {
      status.textContent = '🔲 ' + t('reading_qr');
      const codes = await decodeQR(f);
      if (codes.length) {
        status.textContent = '✅ ' + t('qr_found');
        useQR(codes);
        if (!ta.value.trim()) { state.source = 'qr'; }
        return run();
      }
      status.textContent = '📝 ' + t('reading_text') + ' 0%';
      const text = await readText(f, store.lang, (p) => { status.textContent = '📝 ' + t('reading_text') + ' ' + Math.round(p * 100) + '%'; });
      if (!text.trim()) { status.textContent = '⚠️ ' + t('no_text_found'); return; }
      editMode(); ta.value = text.trim(); state.source = 'ocr';
      status.textContent = '';
      await run();
    } catch (e) {
      status.textContent = '⚠️ ' + e.message;
    }
  }

  function editMode() {
    clear(bubble).append(ta); legendBox.classList.add('hide'); edit.classList.add('hide'); ta.focus();
  }
  edit.addEventListener('click', editMode);
  ta.addEventListener('input', () => { if (state.source === 'ocr') state.source = 'text'; });

  async function run() {
    const text = ta.value.trim() || lastText;
    if (!text && !state.qr.length) { ta.focus(); return; }
    lastText = text;
    btn.disabled = true; btn.textContent = t('checking');
    try {
      let res;
      try { res = await scan({ text, source: state.source, intent: state.intent, qr: state.qr }); }
      catch (e) { if (!isNetworkError(e)) throw e; res = await offlineScan({ text, intent: state.intent, qr: state.qr }); }  // no connection: limited local check
      const shown = res.text_used || text;
      clear(outEl).append(verdictView(res, shown, { showMessage: false, rescan: run, evidenceCtx: { text: shown, source: state.source === 'ocr' ? 'text' : state.source, intent: state.intent, qr: state.qr } }));
      if (shown) { clear(bubble).append(highlighted(shown, res.highlights)); legendBox.classList.remove('hide'); edit.classList.remove('hide'); }
      markActive();
      outEl.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
    } catch (e) {
      clear(outEl).append(h('div', { class: 'note warn' }, '⚠️ ' + e.message));
    } finally {
      btn.disabled = false; btn.textContent = t('check');
    }
  }
  btn.addEventListener('click', () => { if (state.source === 'qr' && ta.value.trim()) state.source = 'text'; run(); });
  ta.addEventListener('keydown', (e) => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') run(); });

  getSamples().then((list) => {
    chips.append(h('span', { class: 'small muted' }, t('try_sample') + ':'));
    list.forEach((s) => chips.append(h('button', { class: 'chip', type: 'button', onclick: () => { editMode(); state.source = 'text'; state.qr = []; intentBox.classList.add('hide'); ta.value = s.text; run(); } }, s.label)));
  }).catch(() => {});

  return h('div', {}, phone, h('div', { class: 'row', style: { justifyContent: 'center', marginTop: '16px' } }, btn, edit), chips, drop, h('div', { class: 'row', style: { justifyContent: 'center', marginTop: '10px' } }, camBtn), camBox, status, intentBox);
}
