// Account page: log in, create account (with a one-time recovery code), profile, export, change password, delete.
import { h, clear, toast } from '../ui.js';
import { at } from '../account_text.js';
import { acct, onAccount, register, login, logout, resetPassword, changePassword, deleteAccount, exportData } from '../account.js';
import { store, level, streakDays, save } from '../store.js';

export function render(root) {
  const page = h('section', { class: 'page wrap stack', style: { maxWidth: '560px' } });
  root.append(page);
  let mode = 'login', pending = null, wasIn = !!acct.user;
  const syncChip = h('span', { class: 'chip' });

  const field = (label, input, hint) => h('label', { class: 'lab' }, h('span', {}, label), input, hint ? h('span', { class: 'small muted' }, hint) : null);
  const input = (type, name, auto, extra = {}) => h('input', { class: 'field', type, name, autocomplete: auto, required: true, ...extra });
  const errBox = () => h('div', { class: 'note warn hide', role: 'alert' });
  const showErr = (box, msg) => { box.textContent = '⚠️ ' + msg; box.classList.remove('hide'); };
  function submitWith(form, btn, box, label, action) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault(); box.classList.add('hide');
      btn.disabled = true; btn.textContent = at('working');
      try { await action(); } catch (err) { showErr(box, err.message); }
      finally { btn.disabled = false; btn.textContent = label; }
    });
  }

  function draw() {
    wasIn = !!acct.user;
    clear(page).append(h('h1', {}, at('title')), h('p', { class: 'lead muted' }, at('sub')));
    if (pending) return page.append(codeCard());
    if (acct.user) return page.append(...profile());
    page.append(guest());
  }

  // ---------- logged out ----------
  function guest() {
    const tabs = h('div', { class: 'tabsm' },
      ...[['login', 'tab_login'], ['create', 'tab_create']].map(([m, k]) => h('button', { class: 'pill', type: 'button', 'aria-pressed': String(mode === m), onclick: () => { mode = m; draw(); } }, at(k))));
    const box = errBox();
    let form, btn;
    if (mode === 'login') {
      const u = input('text', 'username', 'username', { autocapitalize: 'none', spellcheck: 'false' }), p = input('password', 'password', 'current-password');
      btn = h('button', { class: 'btn', type: 'submit' }, at('login_btn'));
      form = h('form', { class: 'stack' }, field(at('username'), u), field(at('password'), p), box, btn,
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => { mode = 'reset'; draw(); } }, at('forgot')));
      submitWith(form, btn, box, at('login_btn'), async () => { await login({ username: u.value, password: p.value }); toast('✅ ' + at('sync_saved')); draw(); });
    } else if (mode === 'create') {
      const u = input('text', 'username', 'username', { autocapitalize: 'none', spellcheck: 'false', pattern: '[A-Za-z0-9_.]{3,30}', maxlength: '30' }), d = h('input', { class: 'field', type: 'text', name: 'display', autocomplete: 'nickname', maxlength: '40' });
      const p = input('password', 'new-password', 'new-password', { minlength: '8', maxlength: '128' }), c = input('password', 'confirm', 'new-password');
      btn = h('button', { class: 'btn', type: 'submit' }, at('create_btn'));
      form = h('form', { class: 'stack' }, field(at('username'), u, at('username_hint')), field(at('display'), d), field(at('password'), p, at('password_hint')), field(at('confirm'), c),
        h('p', { class: 'small muted' }, at('keeps')), box, btn);
      submitWith(form, btn, box, at('create_btn'), async () => {
        if (p.value !== c.value) throw new Error(at('mismatch'));
        pending = { code: await register({ username: u.value, password: p.value, display_name: d.value }) }; draw();
      });
    } else {
      const u = input('text', 'username', 'username', { autocapitalize: 'none' }), r = input('text', 'recovery', 'off', { autocapitalize: 'characters', spellcheck: 'false' }), n = input('password', 'new-password', 'new-password', { minlength: '8' });
      btn = h('button', { class: 'btn', type: 'submit' }, at('reset_btn'));
      form = h('form', { class: 'stack' }, h('h2', {}, at('reset_title')), field(at('username'), u), field(at('recovery'), r), field(at('new_password'), n), box, btn,
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => { mode = 'login'; draw(); } }, at('tab_login')));
      submitWith(form, btn, box, at('reset_btn'), async () => { pending = { code: await resetPassword({ username: u.value, recovery_code: r.value, new_password: n.value }), reset: true }; mode = 'login'; draw(); });
    }
    return h('div', { class: 'stack' }, h('div', { class: 'note' }, '👤 ' + at('guest_note')), h('div', { class: 'card stack' }, mode === 'reset' ? null : tabs, form),
      h('div', { class: 'card flat' }, h('h3', {}, at('data_title')), h('p', { class: 'small' }, at('data_body'))));
  }

  // ---------- recovery code ----------
  function codeCard() {
    const ok = h('input', { type: 'checkbox', id: 'rc-ok' });
    const go = h('button', { class: 'btn', type: 'button', disabled: true, onclick: () => { pending = null; draw(); } }, at('rc_continue'));
    ok.addEventListener('change', () => { go.disabled = !ok.checked; });
    return h('div', { class: 'card stack' }, h('h2', {}, at('rc_title')), pending.reset ? h('p', {}, at('reset_done')) : null, h('p', {}, at('rc_body')),
      h('div', { class: 'display', style: { fontSize: '1.7rem', letterSpacing: '.08em', textAlign: 'center', padding: '14px', border: '3px dashed var(--ink)', borderRadius: '14px', background: 'var(--marigold-soft)', userSelect: 'all' } }, pending.code),
      h('div', { class: 'row' },
        h('button', { class: 'btn small ghost', type: 'button', onclick: async () => { try { await navigator.clipboard.writeText(pending.code); toast(at('copied')); } catch (e) { toast(pending.code); } } }, '📋 ' + at('rc_copy')),
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => download('scamdojo-recovery-code.txt', 'ScamDojo recovery code for ' + (acct.user ? acct.user.username : 'your account') + ':\n' + pending.code + '\n', 'text/plain') }, '⬇️ ' + at('rc_download'))),
      h('label', { class: 'row' }, ok, h('span', {}, at('rc_saved'))), go);
  }

  // ---------- logged in ----------
  function profile() {
    const u = acct.user;
    const created = new Date(u.created_at * 1000).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    paintSync();
    const out = [h('div', { class: 'card stack' },
      h('div', { class: 'row' }, h('h2', { style: { margin: 0 } }, at('hi_user') + ', ' + u.display_name), syncChip),
      h('div', { class: 'muted' }, '@' + u.username + ' · ' + at('member_since') + ' ' + created),
      h('div', { class: 'row' }, h('span', { class: 'chip' }, 'Lv ' + level()), h('span', { class: 'chip' }, store.xp + ' XP'), h('span', { class: 'chip' }, '🔥 ' + streakDays()), h('span', { class: 'chip' }, '🏅 ' + Object.keys(store.badges).length)),
      h('div', { class: 'row' },
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => download('scamdojo-my-data.json', JSON.stringify(exportData(), null, 2), 'application/json') }, '⬇️ ' + at('download')),
        h('button', { class: 'btn small', type: 'button', onclick: async () => { await logout(); draw(); } }, at('logout')))),
      h('div', { class: 'card flat' }, h('h3', {}, at('data_title')), h('p', { class: 'small' }, at('data_body')))];

    // privacy and community (both off until the user turns them on)
    const toggle = (key, label) => { const c = h('input', { type: 'checkbox' }); c.checked = !!store[key]; c.addEventListener('change', () => { store[key] = c.checked; save(); if (key === 'saveHistory') loadHistory(); }); return h('label', { class: 'row' }, c, h('span', {}, label)); };
    const histBox = h('div', { class: 'small' });
    const loadHistory = async () => {
      clear(histBox);
      if (!store.saveHistory) return;
      try {
        const r = await (await fetch('/api/history', { credentials: 'same-origin' })).json();
        histBox.append(h('h3', {}, at('history_title')), r.rows && r.rows.length ? h('ul', {}, r.rows.slice(0, 10).map((x) => h('li', {}, new Date(x.created_at * 1000).toLocaleString() + ' · ' + x.verdict.toUpperCase() + ' ' + Math.round(x.risk * 100) + '%' + (x.categories.length ? ' · ' + x.categories.join(', ') : '') + ' · ' + x.source))) : h('p', { class: 'muted' }, at('history_empty')),
          r.rows && r.rows.length ? h('button', { class: 'btn small ghost', type: 'button', onclick: async () => { await fetch('/api/history', { method: 'DELETE', credentials: 'same-origin' }); loadHistory(); } }, at('clear_history')) : null);
      } catch (e) { /* offline: skip */ }
    };
    out.push(h('div', { class: 'card flat stack' }, h('h3', {}, at('priv_title')), toggle('saveHistory', at('save_history')), toggle('leaderboard', at('leaderboard_opt')), histBox));
    loadHistory();

    // change password
    const cb = errBox(), cur = input('password', 'current', 'current-password'), nw = input('password', 'new', 'new-password', { minlength: '8' });
    const cbtn = h('button', { class: 'btn small', type: 'submit' }, at('save_pw'));
    const cform = h('form', { class: 'stack' }, field(at('current_pw'), cur), field(at('new_password'), nw), cb, cbtn);
    submitWith(cform, cbtn, cb, at('save_pw'), async () => { await changePassword(cur.value, nw.value); cur.value = nw.value = ''; toast(at('pw_changed')); });
    out.push(h('details', { class: 'card flat' }, h('summary', {}, h('b', {}, at('change_pw'))), cform));

    // delete
    const db = errBox(), dp = input('password', 'delete', 'current-password');
    const dbtn = h('button', { class: 'btn scam small', type: 'submit' }, at('delete_btn'));
    const dform = h('form', { class: 'stack' }, h('p', { class: 'small' }, at('delete_body')), field(at('delete_confirm'), dp), db, dbtn);
    submitWith(dform, dbtn, db, at('delete_btn'), async () => { await deleteAccount(dp.value); toast(at('deleted')); draw(); });
    out.push(h('details', { class: 'card flat' }, h('summary', {}, h('b', {}, at('delete_title'))), dform));
    return out;
  }

  function paintSync() {
    const k = { local: 'sync_local', saving: 'sync_saving', saved: 'sync_saved', error: 'sync_error' }[acct.sync] || 'sync_local';
    syncChip.textContent = (acct.sync === 'saved' ? '✅ ' : acct.sync === 'error' ? '⚠️ ' : '⏳ ') + at(k);
  }
  const off = onAccount(() => { if (!!acct.user !== wasIn && !pending) draw(); else paintSync(); });
  draw();
  return off;
}

function download(name, text, type) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name;
  document.body.append(a); a.click(); a.remove();
}
