// Makes a shareable result image on a canvas, entirely in the browser.
import { toast } from './ui.js';

export async function shareImage({ title, big, lines = [], accent = '#FFB400', filename = 'scamdojo-result.png' }) {
  const c = document.createElement('canvas');
  c.width = c.height = 1080;
  const g = c.getContext('2d');
  g.fillStyle = '#EEF1F6'; g.fillRect(0, 0, 1080, 1080);
  g.fillStyle = accent; g.fillRect(0, 0, 1080, 300);
  g.strokeStyle = '#1B1F4B'; g.lineWidth = 12; g.strokeRect(24, 24, 1032, 1032);
  g.fillStyle = '#1B1F4B';
  g.font = '800 92px Bungee, Impact, "Arial Black", sans-serif'; g.textAlign = 'center';
  g.fillText('ScamDojo', 540, 190);
  g.font = '700 58px Hind, "Segoe UI", sans-serif';
  g.fillText(title, 540, 420);
  g.font = '800 230px Bungee, Impact, "Arial Black", sans-serif';
  g.fillStyle = '#D6247F';
  g.fillText(big, 540, 680);
  g.fillStyle = '#1B1F4B'; g.font = '600 46px Hind, "Segoe UI", sans-serif';
  lines.slice(0, 3).forEach((l, i) => g.fillText(l, 540, 780 + i * 66));
  g.font = '600 34px Hind, "Segoe UI", sans-serif'; g.fillStyle = '#4A4F7A';
  g.fillText('Can you spot the scam? Try it yourself.', 540, 1010);
  const blob = await new Promise((r) => c.toBlob(r, 'image/png'));
  const file = new File([blob], filename, { type: 'image/png' });
  try {
    if (navigator.canShare && navigator.canShare({ files: [file] })) {
      await navigator.share({ files: [file], title: 'ScamDojo', text: title + ' ' + big });
      return;
    }
  } catch (e) { /* user cancelled or unsupported: fall back to download */ }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = filename;
  document.body.append(a); a.click(); a.remove();
  toast('Image saved');
}

/** Share a link with the phone's share sheet, or copy it. */
export async function shareLink({ title, text, url }) {
  try { if (navigator.share) { await navigator.share({ title, text, url }); return; } } catch (e) { return; }
  try { await navigator.clipboard.writeText(url); toast('Link copied'); } catch (e) { toast(url); }
}
