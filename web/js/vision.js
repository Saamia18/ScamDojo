// Reads screenshots (OCR) and QR codes entirely in the browser. Images are never uploaded.
// QR: the native BarcodeDetector when the browser has it (Chrome on Android), otherwise jsQR.
// OCR: Tesseract.js. Both libraries are loaded on demand from a CDN the first time they are needed.
const TESSERACT = 'https://cdn.jsdelivr.net/npm/tesseract.js@5.1.1/dist/tesseract.min.js';
const JSQR = 'https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js';
const loaded = {};

export function loadScript(src) {
  loaded[src] = loaded[src] || new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = src; s.async = true; s.onload = resolve;
    s.onerror = () => { delete loaded[src]; reject(new Error('Could not load the image reader. Check your internet connection and try again.')); };
    document.head.append(s);
  });
  return loaded[src];
}

/** Draw an image file onto a canvas no bigger than maxSide. */
export async function fileToCanvas(file, maxSide = 1800) {
  const bmp = await createImageBitmap(file);
  const scale = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
  const c = document.createElement('canvas');
  c.width = Math.max(1, Math.round(bmp.width * scale)); c.height = Math.max(1, Math.round(bmp.height * scale));
  c.getContext('2d', { willReadFrequently: true }).drawImage(bmp, 0, 0, c.width, c.height);
  if (bmp.close) bmp.close();
  return c;
}

async function detectQR(canvas) {
  if ('BarcodeDetector' in window) {
    try {
      const formats = (BarcodeDetector.getSupportedFormats && await BarcodeDetector.getSupportedFormats()) || ['qr_code'];
      if (formats.includes('qr_code')) {
        const found = await new BarcodeDetector({ formats: ['qr_code'] }).detect(canvas);
        if (found.length) return [...new Set(found.map((f) => f.rawValue))];
      }
    } catch (e) { /* fall through to jsQR */ }
  }
  await loadScript(JSQR);
  const img = canvas.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, canvas.width, canvas.height);
  const r = window.jsQR(img.data, img.width, img.height, { inversionAttempts: 'attemptBoth' });
  return r && r.data ? [r.data] : [];
}

/** Returns the decoded QR payload strings found in an image file (usually zero or one). */
export async function decodeQR(file) {
  for (const side of [1600, 800]) {  // a second, smaller pass helps with very large photos
    const found = await detectQR(await fileToCanvas(file, side));
    if (found.length) return found;
  }
  return [];
}

/** OCR the text in a screenshot. onProgress receives a number from 0 to 1. */
export async function readText(file, uiLang, onProgress) {
  await loadScript(TESSERACT);
  const langs = uiLang === 'hi' ? 'eng+hin' : uiLang === 'kn' ? 'eng+kan' : 'eng';
  const worker = await window.Tesseract.createWorker(langs, 1, {
    logger: (m) => { if (onProgress && m && m.status === 'recognizing text') onProgress(m.progress || 0); },
  });
  try {
    const { data } = await worker.recognize(await fileToCanvas(file, 2200));
    return (data && data.text) || '';
  } finally {
    await worker.terminate();
  }
}

/** Live camera QR scanning. Returns { stop } and calls onCode(payload) once. */
export async function scanWithCamera(video, onCode, onError) {
  let stream, timer, stopped = false;
  const stop = () => { stopped = true; clearInterval(timer); if (stream) stream.getTracks().forEach((t) => t.stop()); video.srcObject = null; };
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
    video.srcObject = stream; video.setAttribute('playsinline', ''); await video.play();
    const canvas = document.createElement('canvas');
    let busy = false;
    timer = setInterval(async () => {
      if (stopped || busy || !video.videoWidth) return;
      busy = true;
      try {
        const scale = Math.min(1, 900 / video.videoWidth);
        canvas.width = Math.round(video.videoWidth * scale); canvas.height = Math.round(video.videoHeight * scale);
        canvas.getContext('2d', { willReadFrequently: true }).drawImage(video, 0, 0, canvas.width, canvas.height);
        const found = await detectQR(canvas);
        if (found.length && !stopped) { stop(); onCode(found[0]); }
      } catch (e) { if (!stopped) { stop(); onError(e); } }
      busy = false;
    }, 250);
  } catch (e) {
    stop(); onError(new Error('Camera not available. Allow camera access, or upload a photo of the QR code instead.'));
  }
  return { stop };
}
