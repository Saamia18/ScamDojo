import { store, save } from './store.js';
let ctx;
function tone(freq, start, dur, type = 'square', vol = 0.06) {
  const o = ctx.createOscillator(), g = ctx.createGain();
  o.type = type; o.frequency.value = freq;
  g.gain.setValueAtTime(vol, ctx.currentTime + start);
  g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + start + dur);
  o.connect(g); g.connect(ctx.destination);
  o.start(ctx.currentTime + start); o.stop(ctx.currentTime + start + dur + 0.02);
}
const SOUNDS = {
  good: () => { tone(660, 0, 0.09); tone(880, 0.09, 0.14); },
  bad: () => { tone(180, 0, 0.25, 'sawtooth', 0.07); },
  crit: () => { tone(880, 0, 0.08); tone(1100, 0.08, 0.08); tone(1320, 0.16, 0.18); },
  win: () => { [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.12, 0.2)); },
  lose: () => { [392, 330, 262, 196].forEach((f, i) => tone(f, i * 0.16, 0.25, 'triangle', 0.08)); },
  tap: () => tone(500, 0, 0.04, 'square', 0.03),
};
export function play(name) {
  if (!store.sound) return;
  try {
    ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') ctx.resume();
    SOUNDS[name] && SOUNDS[name]();
  } catch (e) { /* audio not available */ }
}
export function toggleSound() { store.sound = !store.sound; save(); return store.sound; }
