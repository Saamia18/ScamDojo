import { h } from '../ui.js';
import { buildScanner } from '../scanner.js';
import { t } from '../i18n.js';

export function render(root) {
  const out = h('div', { class: 'stack', style: { marginTop: '26px' } });
  root.append(h('section', { class: 'page wrap' },
    h('h1', {}, t('nav_scan')),
    h('p', { class: 'lead muted' }, t('hero_sub')),
    buildScanner(out), out));
}
