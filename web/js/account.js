// Account state and server sync. Guests keep everything in localStorage; logged-in users also save progress to the server.
import { store, save, setSaveHook, snapshot, mergeProgress, wipeLocal } from './store.js';

export const acct = { user: null, sync: 'local' }; // sync: local | saving | saved | error
const listeners = new Set();
export const onAccount = (f) => { listeners.add(f); return () => listeners.delete(f); };
const emit = () => listeners.forEach((f) => { try { f(); } catch (e) { /* ignore */ } });

async function api(method, path, body) {
  try {
    const r = await fetch(path, { method, credentials: 'same-origin', headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
    const data = await r.json().catch(() => ({}));
    return { ok: r.ok, status: r.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { error: 'Cannot reach the server. Check your connection and try again.' } };
  }
}

let timer = null;
export function scheduleSync(now) {
  if (!acct.user) return;
  clearTimeout(timer);
  acct.sync = 'saving'; emit();
  timer = setTimeout(push, now ? 0 : 1200);
}
async function push() {
  if (!acct.user) return;
  const r = await api('PUT', '/api/progress', { progress: snapshot() });
  if (r.status === 401) { acct.user = null; acct.sync = 'local'; }
  else acct.sync = r.ok ? 'saved' : 'error';
  emit();
  if (!r.ok && r.status !== 401) timer = setTimeout(push, 8000);
}
setSaveHook(() => scheduleSync());

function adopt(progress, takePrefs) {
  mergeProgress(progress, takePrefs);
  save(true);
}

export async function init() {
  const r = await api('GET', '/api/me');
  if (r.ok && r.data.user) {
    acct.user = r.data.user; acct.sync = 'saved';
    adopt(r.data.progress, true);
    scheduleSync();
  }
  emit();
}

export async function register({ username, password, display_name }) {
  const r = await api('POST', '/api/auth/register', { username, password, display_name, progress: snapshot() });
  if (!r.ok) throw new Error(r.data.error || 'Could not create the account.');
  acct.user = r.data.user; acct.sync = 'saved'; emit();
  return r.data.recovery_code;
}

export async function login({ username, password }) {
  const r = await api('POST', '/api/auth/login', { username, password });
  if (!r.ok) throw new Error(r.data.error || 'Could not log in.');
  acct.user = r.data.user;
  adopt(r.data.progress, true);
  scheduleSync(true);
}

export async function logout() {
  await api('POST', '/api/auth/logout', {});
  acct.user = null; acct.sync = 'local';
  wipeLocal(); emit();
}

export async function resetPassword({ username, recovery_code, new_password }) {
  const r = await api('POST', '/api/auth/reset', { username, recovery_code, new_password });
  if (!r.ok) throw new Error(r.data.error || 'Could not reset the password.');
  return r.data.recovery_code;
}

export async function changePassword(current, next) {
  const r = await api('POST', '/api/auth/password', { current, new: next });
  if (!r.ok) throw new Error(r.data.error || 'Could not change the password.');
}

export async function deleteAccount(password) {
  const r = await api('POST', '/api/auth/delete', { password });
  if (!r.ok) throw new Error(r.data.error || 'Could not delete the account.');
  acct.user = null; acct.sync = 'local'; wipeLocal(); emit();
}

export const exportData = () => ({ exported_at: new Date().toISOString(), user: acct.user, progress: snapshot() });
