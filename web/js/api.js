let cardsPromise = null;
async function j(url, opts) {
  const r = await fetch(url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || 'Request failed (' + r.status + ')');
  return data;
}
export const analyze = (text) => j('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
export const getCards = () => (cardsPromise = cardsPromise || j('/api/cards'));
export const getMetrics = () => j('/api/metrics');
export const getSamples = () => j('/api/samples');
export const scan = (payload) => j('/api/scan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
export const getConfig = () => j('/api/config');
export const buildEvidence = (payload) => j('/api/evidence', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
export const generateCards = (category, lang, count) => j('/api/cards/generate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ category, lang, count }) });
