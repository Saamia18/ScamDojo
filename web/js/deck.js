// Adaptive card selection: scam types the player misses more often are served more often.
import { weightFor } from './store.js';
import { shuffle } from './ui.js';

const w = (c) => weightFor(c) * (c.generated ? 1.6 : 1);  // fresh AI-generated cards are served a little more often
const key = (c) => Math.pow(Math.random(), 1 / w(c));

export function pickDeck(cards, nScam, nLegit) {
  const top = (flag, n) => cards.filter((c) => c.scam === flag).map((c) => ({ c, k: key(c) })).sort((a, b) => b.k - a.k).slice(0, n).map((x) => x.c);
  return shuffle([...top(true, nScam), ...top(false, nLegit)]);
}

/** Endless supply for Inbox Rush: weighted random, never repeating the last dozen cards. */
export function endlessPicker(cards) {
  const recent = [];
  return () => {
    const pool = cards.filter((c) => !recent.includes(c.id));
    const weights = pool.map((c) => w(c) * (c.scam ? 1.4 : 1));
    let r = Math.random() * weights.reduce((a, b) => a + b, 0), pick = pool[0];
    for (let i = 0; i < pool.length; i++) { r -= weights[i]; if (r <= 0) { pick = pool[i]; break; } }
    recent.push(pick.id);
    if (recent.length > 12) recent.shift();
    return pick;
  };
}
