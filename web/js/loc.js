// Shows cards and bosses in the player's language. The AI verdict always comes from the English original;
// highlights in translations come from hand-checked red-flag phrases plus the link positions.
import { store } from './store.js';

export function localize(card) {
  const tr = store.lang !== 'en' && card.i18n && card.i18n[store.lang];
  if (!tr) return card;
  const hl = [];
  for (const f of tr.flags || []) {
    const i = tr.text.indexOf(f);
    if (i >= 0) hl.push({ start: i, end: i + f.length, kind: 'rule', label: f });
  }
  for (const l of (card.ai && card.ai.links) || []) {
    const i = tr.text.indexOf(l.url);
    if (i >= 0) hl.push({ start: i, end: i + l.url.length, kind: 'link', label: l.url });
  }
  hl.sort((a, b) => a.start - b.start);
  const clean = [];
  for (const h of hl) if (!clean.length || h.start >= clean[clean.length - 1].end) clean.push(h);
  return { ...card, text: tr.text, lesson: tr.lesson, translated: true, ai: { ...card.ai, highlights: clean } };
}

export function bossText(boss) {
  const tr = store.lang !== 'en' && boss.i18n && boss.i18n[store.lang];
  return tr ? { ...boss, ...tr } : boss;
}
