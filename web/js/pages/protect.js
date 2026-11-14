// Protect: the practical side. A security checkup, and what to do if you have already been scammed.
// Everything stays on the device. The complaint summary is always written in English for the authorities.
import { h, clear, toast } from '../ui.js';
import { store, markActive, save, today } from '../store.js';
import { listenButton } from '../speech.js';

const P = {
  en: {
    title: 'Protect yourself', sub: 'Two things that work in real life: a quick security checkup, and what to do if you have already been scammed.',
    check_title: 'Security checkup', check_sub: 'Answer honestly. Your answers stay on your device; only the score is saved if you are logged in.', yes: 'Yes', no: 'No', strong: 'Strong', fair: 'Fair', risk: 'At risk', score: 'Your score', fix: 'Fix these first', restart: 'Start again',
    q: ['I never share my OTP, UPI PIN or CVV with anyone.', 'I turned on two-step verification on my email and WhatsApp.', 'I only install apps from the Play Store or App Store.', 'My phone and apps are updated and the screen is locked.', 'Before logging in I check the website address (typed by me, or the official app).', 'My email and my bank use different passwords.', 'I set a daily UPI or card limit and have bank SMS alerts on.', 'I know the cyber crime helpline is 1930.'],
    tip: ['Share nothing. Banks never ask. Hang up and call the number printed on your card.', 'Turn on two-step verification: WhatsApp Settings > Account > Two-step verification, and Security in your Google account.', 'Delete apps installed from links and switch off "install unknown apps".', 'Turn on automatic updates and set a screen lock (PIN, fingerprint or face).', 'Do not open links in messages. Open the app, or type the website yourself.', 'Use a different password for email and banking. A password manager helps.', 'Set a daily UPI limit in your payment app and keep bank SMS alerts on.', 'Save 1930 in your phone. Report at cybercrime.gov.in.'],
    scam_title: 'I have been scammed. What now?',
    steps: ['Call your bank right now (number on your card). Ask them to block the card or UPI and to stop the transaction.', 'Call 1930, the National Cyber Crime Helpline, as soon as you can. The first hours matter most.', 'Report at cybercrime.gov.in with screenshots, transaction IDs, and the scammer\'s phone number or UPI ID.', 'Change passwords and PINs for the affected accounts and log out of all devices.', 'Do not pay a "recovery fee" to anyone who contacts you about getting your money back.'],
    form_title: 'Complaint summary', f_type: 'What happened', types: ['Fake KYC / bank call or SMS', 'OTP or UPI PIN shared', 'UPI collect request / QR', 'Fake job or investment', 'Prize or lottery', 'Parcel / customs / police threat', 'Other'],
    f_amount: 'Amount lost (₹)', f_when: 'Date and time', f_how: 'How you paid', hows: ['UPI', 'Debit/credit card', 'Net banking', 'Cash or other'], f_who: 'Scammer phone number, UPI ID or link', f_story: 'What happened, in a few lines',
    make: 'Create summary', copy: 'Copy', copied: 'Copied', helpline: 'Call 1930', portal: 'Open cybercrime.gov.in', note: 'This text stays on your device. Read it out to 1930 or paste it into the complaint form. It is written in English.',
  },
  hi: {
    title: 'खुद को सुरक्षित रखें', sub: 'असल ज़िंदगी में काम आने वाली दो चीज़ें: एक छोटा सुरक्षा चेकअप, और ठगी हो जाने पर क्या करें।',
    check_title: 'सुरक्षा चेकअप', check_sub: 'ईमानदारी से जवाब दें। आपके जवाब आपके डिवाइस पर रहते हैं; लॉग इन होने पर सिर्फ़ स्कोर सेव होता है।', yes: 'हाँ', no: 'नहीं', strong: 'मज़बूत', fair: 'ठीक-ठाक', risk: 'ख़तरे में', score: 'आपका स्कोर', fix: 'पहले इन्हें ठीक करें', restart: 'फिर से शुरू करें',
    q: ['मैं अपना OTP, UPI PIN या CVV किसी को नहीं बताता/बताती।', 'मैंने अपने ईमेल और WhatsApp पर टू-स्टेप वेरिफ़िकेशन चालू किया है।', 'मैं ऐप सिर्फ़ Play Store या App Store से इंस्टॉल करता/करती हूँ।', 'मेरे फ़ोन और ऐप अपडेट हैं और स्क्रीन लॉक लगा है।', 'लॉगिन से पहले मैं वेबसाइट का पता जाँचता/जाँचती हूँ (खुद टाइप करके या आधिकारिक ऐप से)।', 'मेरे ईमेल और बैंक का पासवर्ड अलग-अलग हैं।', 'मैंने UPI/कार्ड की रोज़ की सीमा तय की है और बैंक SMS अलर्ट चालू हैं।', 'मुझे पता है कि साइबर क्राइम हेल्पलाइन 1930 है।'],
    tip: ['किसी को कुछ न बताएँ: बैंक कभी नहीं माँगते। फ़ोन काटें और कार्ड पर छपे नंबर पर कॉल करें।', 'टू-स्टेप वेरिफ़िकेशन चालू करें: WhatsApp सेटिंग्स > खाता > टू-स्टेप वेरिफ़िकेशन, और Google खाते में सुरक्षा।', 'लिंक से इंस्टॉल किए ऐप हटाएँ और "अज्ञात स्रोत से इंस्टॉल" बंद करें।', 'ऑटो-अपडेट चालू करें और स्क्रीन लॉक (PIN, फ़िंगरप्रिंट या चेहरा) लगाएँ।', 'मैसेज के लिंक न खोलें। ऐप खोलें या वेबसाइट खुद टाइप करें।', 'ईमेल और बैंक के लिए अलग पासवर्ड रखें। पासवर्ड मैनेजर मदद करता है।', 'पेमेंट ऐप में UPI की रोज़ की सीमा तय करें और बैंक के SMS अलर्ट चालू रखें।', 'फ़ोन में 1930 सेव करें। रिपोर्ट cybercrime.gov.in पर करें।'],
    scam_title: 'मेरे साथ ठगी हो गई। अब क्या करूँ?',
    steps: ['तुरंत अपने बैंक को कॉल करें (कार्ड पर छपा नंबर) और कार्ड या UPI ब्लॉक करवाएँ तथा लेन-देन रुकवाने को कहें।', 'जितनी जल्दी हो सके 1930 (राष्ट्रीय साइबर क्राइम हेल्पलाइन) पर कॉल करें। शुरुआती घंटे सबसे अहम हैं।', 'cybercrime.gov.in पर स्क्रीनशॉट, लेन-देन आईडी और ठग के फ़ोन नंबर या UPI आईडी के साथ रिपोर्ट करें।', 'प्रभावित खातों के पासवर्ड और PIN बदलें और सभी डिवाइस से लॉग आउट करें।', 'पैसे वापस दिलाने के नाम पर आपसे संपर्क करने वाले किसी को "रिकवरी फ़ीस" न दें।'],
    form_title: 'शिकायत का सारांश', f_type: 'क्या हुआ', types: ['नकली KYC / बैंक कॉल या SMS', 'OTP या UPI PIN बता दिया', 'UPI कलेक्ट रिक्वेस्ट / QR', 'नकली नौकरी या निवेश', 'इनाम या लॉटरी', 'पार्सल / कस्टम्स / पुलिस की धमकी', 'अन्य'],
    f_amount: 'गँवाई रकम (₹)', f_when: 'तारीख और समय', f_how: 'भुगतान कैसे किया', hows: ['UPI', 'डेबिट/क्रेडिट कार्ड', 'नेट बैंकिंग', 'नकद या अन्य'], f_who: 'ठग का फ़ोन नंबर, UPI आईडी या लिंक', f_story: 'क्या हुआ, कुछ पंक्तियों में',
    make: 'सारांश बनाएँ', copy: 'कॉपी करें', copied: 'कॉपी हो गया', helpline: '1930 पर कॉल करें', portal: 'cybercrime.gov.in खोलें', note: 'यह टेक्स्ट आपके डिवाइस पर ही रहता है। इसे 1930 पर पढ़कर सुनाएँ या शिकायत फ़ॉर्म में चिपकाएँ। सारांश अंग्रेज़ी में बनता है।',
  },
  kn: {
    title: 'ನಿಮ್ಮನ್ನು ರಕ್ಷಿಸಿಕೊಳ್ಳಿ', sub: 'ನಿಜ ಜೀವನದಲ್ಲಿ ಕೆಲಸ ಮಾಡುವ ಎರಡು ವಿಷಯಗಳು: ಒಂದು ಸಣ್ಣ ಭದ್ರತಾ ತಪಾಸಣೆ, ಮತ್ತು ಈಗಾಗಲೇ ವಂಚನೆಯಾದರೆ ಏನು ಮಾಡಬೇಕು.',
    check_title: 'ಭದ್ರತಾ ತಪಾಸಣೆ', check_sub: 'ಪ್ರಾಮಾಣಿಕವಾಗಿ ಉತ್ತರಿಸಿ. ನಿಮ್ಮ ಉತ್ತರಗಳು ನಿಮ್ಮ ಸಾಧನದಲ್ಲೇ ಇರುತ್ತವೆ; ಲಾಗಿನ್ ಆಗಿದ್ದರೆ ಅಂಕ ಮಾತ್ರ ಉಳಿಸಲಾಗುತ್ತದೆ.', yes: 'ಹೌದು', no: 'ಇಲ್ಲ', strong: 'ಬಲಿಷ್ಠ', fair: 'ಪರವಾಗಿಲ್ಲ', risk: 'ಅಪಾಯದಲ್ಲಿ', score: 'ನಿಮ್ಮ ಅಂಕ', fix: 'ಮೊದಲು ಇವನ್ನು ಸರಿಪಡಿಸಿ', restart: 'ಮತ್ತೆ ಆರಂಭಿಸಿ',
    q: ['ನಾನು ನನ್ನ OTP, UPI PIN ಅಥವಾ CVV ಅನ್ನು ಯಾರಿಗೂ ಹೇಳುವುದಿಲ್ಲ.', 'ನನ್ನ ಇಮೇಲ್ ಮತ್ತು WhatsApp ನಲ್ಲಿ ಎರಡು ಹಂತದ ಪರಿಶೀಲನೆ ಆನ್ ಮಾಡಿದ್ದೇನೆ.', 'ನಾನು ಆ್ಯಪ್ ಗಳನ್ನು Play Store ಅಥವಾ App Store ನಿಂದ ಮಾತ್ರ ಇನ್ಸ್ಟಾಲ್ ಮಾಡುತ್ತೇನೆ.', 'ನನ್ನ ಫೋನ್ ಮತ್ತು ಆ್ಯಪ್ ಗಳು ಅಪ್ ಡೇಟ್ ಆಗಿವೆ ಮತ್ತು ಸ್ಕ್ರೀನ್ ಲಾಕ್ ಇದೆ.', 'ಲಾಗಿನ್ ಮಾಡುವ ಮೊದಲು ವೆಬ್ ವಿಳಾಸ ಪರಿಶೀಲಿಸುತ್ತೇನೆ (ನಾನೇ ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಅಧಿಕೃತ ಆ್ಯಪ್ ನಲ್ಲಿ).', 'ನನ್ನ ಇಮೇಲ್ ಮತ್ತು ಬ್ಯಾಂಕ್ ಗೆ ಬೇರೆ ಬೇರೆ ಪಾಸ್ ವರ್ಡ್ ಇದೆ.', 'UPI ಅಥವಾ ಕಾರ್ಡ್ ದೈನಂದಿನ ಮಿತಿ ಹಾಕಿದ್ದೇನೆ ಮತ್ತು ಬ್ಯಾಂಕ್ SMS ಎಚ್ಚರಿಕೆ ಆನ್ ಇದೆ.', 'ಸೈಬರ್ ಕ್ರೈಂ ಸಹಾಯವಾಣಿ 1930 ಎಂದು ನನಗೆ ಗೊತ್ತು.'],
    tip: ['ಯಾರಿಗೂ ಏನನ್ನೂ ಹೇಳಬೇಡಿ: ಬ್ಯಾಂಕ್ ಎಂದಿಗೂ ಕೇಳುವುದಿಲ್ಲ. ಕರೆ ಕಡಿತಗೊಳಿಸಿ, ಕಾರ್ಡ್ ಮೇಲಿರುವ ಸಂಖ್ಯೆಗೆ ಕರೆ ಮಾಡಿ.', 'ಎರಡು ಹಂತದ ಪರಿಶೀಲನೆ ಆನ್ ಮಾಡಿ: WhatsApp ಸೆಟ್ಟಿಂಗ್ಸ್ > ಖಾತೆ > ಎರಡು ಹಂತದ ಪರಿಶೀಲನೆ, ಮತ್ತು Google ಖಾತೆಯಲ್ಲಿ ಭದ್ರತೆ.', 'ಲಿಂಕ್ ಮೂಲಕ ಇನ್ಸ್ಟಾಲ್ ಮಾಡಿದ ಆ್ಯಪ್ ಗಳನ್ನು ಅಳಿಸಿ ಮತ್ತು "ಅಜ್ಞಾತ ಮೂಲದಿಂದ ಇನ್ಸ್ಟಾಲ್" ಆಫ್ ಮಾಡಿ.', 'ಸ್ವಯಂ ಅಪ್ ಡೇಟ್ ಆನ್ ಮಾಡಿ ಮತ್ತು ಸ್ಕ್ರೀನ್ ಲಾಕ್ (PIN, ಬೆರಳಚ್ಚು ಅಥವಾ ಮುಖ) ಹಾಕಿ.', 'ಸಂದೇಶದಲ್ಲಿರುವ ಲಿಂಕ್ ತೆರೆಯಬೇಡಿ. ಆ್ಯಪ್ ತೆರೆಯಿರಿ ಅಥವಾ ವೆಬ್ ಸೈಟ್ ನೀವೇ ಟೈಪ್ ಮಾಡಿ.', 'ಇಮೇಲ್ ಮತ್ತು ಬ್ಯಾಂಕ್ ಗೆ ಬೇರೆ ಬೇರೆ ಪಾಸ್ ವರ್ಡ್ ಇಡಿ. ಪಾಸ್ ವರ್ಡ್ ಮ್ಯಾನೇಜರ್ ಸಹಾಯ ಮಾಡುತ್ತದೆ.', 'ಪೇಮೆಂಟ್ ಆ್ಯಪ್ ನಲ್ಲಿ UPI ದೈನಂದಿನ ಮಿತಿ ಹಾಕಿ ಮತ್ತು ಬ್ಯಾಂಕ್ SMS ಎಚ್ಚರಿಕೆ ಆನ್ ಇಡಿ.', 'ಫೋನ್ ನಲ್ಲಿ 1930 ಉಳಿಸಿ. cybercrime.gov.in ನಲ್ಲಿ ವರದಿ ಮಾಡಿ.'],
    scam_title: 'ನನಗೆ ವಂಚನೆಯಾಗಿದೆ. ಈಗ ಏನು ಮಾಡಬೇಕು?',
    steps: ['ತಕ್ಷಣ ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಗೆ ಕರೆ ಮಾಡಿ (ಕಾರ್ಡ್ ಮೇಲಿರುವ ಸಂಖ್ಯೆ), ಕಾರ್ಡ್ ಅಥವಾ UPI ನಿರ್ಬಂಧಿಸಿ ಮತ್ತು ವಹಿವಾಟು ತಡೆಯಲು ಹೇಳಿ.', 'ಸಾಧ್ಯವಾದಷ್ಟು ಬೇಗ 1930 (ರಾಷ್ಟ್ರೀಯ ಸೈಬರ್ ಕ್ರೈಂ ಸಹಾಯವಾಣಿ) ಗೆ ಕರೆ ಮಾಡಿ. ಮೊದಲ ಕೆಲವು ಗಂಟೆಗಳು ಅತ್ಯಂತ ಮುಖ್ಯ.', 'cybercrime.gov.in ನಲ್ಲಿ ಸ್ಕ್ರೀನ್ ಶಾಟ್, ವಹಿವಾಟು ಐಡಿ ಮತ್ತು ವಂಚಕನ ಫೋನ್ ಸಂಖ್ಯೆ ಅಥವಾ UPI ಐಡಿಯೊಂದಿಗೆ ವರದಿ ಮಾಡಿ.', 'ಬಾಧಿತ ಖಾತೆಗಳ ಪಾಸ್ ವರ್ಡ್ ಮತ್ತು PIN ಬದಲಿಸಿ, ಎಲ್ಲಾ ಸಾಧನಗಳಿಂದ ಲಾಗ್ ಔಟ್ ಆಗಿ.', 'ಹಣ ವಾಪಸ್ ಕೊಡಿಸುತ್ತೇವೆ ಎಂದು ಸಂಪರ್ಕಿಸುವ ಯಾರಿಗೂ "ರಿಕವರಿ ಶುಲ್ಕ" ಕೊಡಬೇಡಿ.'],
    form_title: 'ದೂರಿನ ಸಾರಾಂಶ', f_type: 'ಏನಾಯಿತು', types: ['ನಕಲಿ KYC / ಬ್ಯಾಂಕ್ ಕರೆ ಅಥವಾ SMS', 'OTP ಅಥವಾ UPI PIN ಹೇಳಿದ್ದೇನೆ', 'UPI ಕಲೆಕ್ಟ್ ವಿನಂತಿ / QR', 'ನಕಲಿ ಉದ್ಯೋಗ ಅಥವಾ ಹೂಡಿಕೆ', 'ಬಹುಮಾನ ಅಥವಾ ಲಾಟರಿ', 'ಪಾರ್ಸೆಲ್ / ಕಸ್ಟಮ್ಸ್ / ಪೊಲೀಸ್ ಬೆದರಿಕೆ', 'ಇತರೆ'],
    f_amount: 'ಕಳೆದುಕೊಂಡ ಮೊತ್ತ (₹)', f_when: 'ದಿನಾಂಕ ಮತ್ತು ಸಮಯ', f_how: 'ಪಾವತಿ ಹೇಗೆ ಮಾಡಿದಿರಿ', hows: ['UPI', 'ಡೆಬಿಟ್/ಕ್ರೆಡಿಟ್ ಕಾರ್ಡ್', 'ನೆಟ್ ಬ್ಯಾಂಕಿಂಗ್', 'ನಗದು ಅಥವಾ ಇತರೆ'], f_who: 'ವಂಚಕನ ಫೋನ್ ಸಂಖ್ಯೆ, UPI ಐಡಿ ಅಥವಾ ಲಿಂಕ್', f_story: 'ಏನಾಯಿತು, ಕೆಲವು ಸಾಲುಗಳಲ್ಲಿ',
    make: 'ಸಾರಾಂಶ ರಚಿಸಿ', copy: 'ನಕಲಿಸಿ', copied: 'ನಕಲಿಸಲಾಗಿದೆ', helpline: '1930 ಗೆ ಕರೆ ಮಾಡಿ', portal: 'cybercrime.gov.in ತೆರೆಯಿರಿ', note: 'ಈ ಪಠ್ಯ ನಿಮ್ಮ ಸಾಧನದಲ್ಲೇ ಇರುತ್ತದೆ. ಇದನ್ನು 1930 ಗೆ ಓದಿ ಹೇಳಿ ಅಥವಾ ದೂರು ಫಾರ್ಮ್ ನಲ್ಲಿ ಅಂಟಿಸಿ. ಸಾರಾಂಶ ಇಂಗ್ಲಿಷ್ ನಲ್ಲಿ ರಚನೆಯಾಗುತ್ತದೆ.',
  },
};

export function render(root) {
  const L = P[store.lang] || P.en, EN = P.en;
  const lang = store.lang;
  const page = h('section', { class: 'page wrap stack', style: { maxWidth: '760px' } },
    h('h1', {}, L.title), h('p', { class: 'lead muted' }, L.sub));
  root.append(page);

  // ---------- security checkup ----------
  const answers = new Array(L.q.length).fill(null);
  let recorded = false;
  const box = h('div', { class: 'card stack' });
  page.append(box);
  function drawCheckup() {
    clear(box).append(h('div', { class: 'row' }, h('h2', { style: { margin: 0 } }, L.check_title), listenButton(() => [{ text: L.check_sub + ' ' + L.q.join(' '), lang }])), h('p', { class: 'muted' }, L.check_sub));
    L.q.forEach((q, i) => {
      const yes = h('button', { class: 'btn small' + (answers[i] === true ? '' : ' ghost'), type: 'button', 'aria-pressed': String(answers[i] === true) }, L.yes);
      const no = h('button', { class: 'btn small' + (answers[i] === false ? '' : ' ghost'), type: 'button', 'aria-pressed': String(answers[i] === false) }, L.no);
      yes.addEventListener('click', () => { answers[i] = true; markActive(); drawCheckup(); });
      no.addEventListener('click', () => { answers[i] = false; markActive(); drawCheckup(); });
      box.append(h('div', { class: 'reason' }, h('div', {}, q), h('div', { class: 'row', style: { marginTop: '8px' } }, yes, no)));
    });
    if (answers.every((a) => a !== null)) {
      const good = answers.filter(Boolean).length;
      if (!recorded) { recorded = true; store.checkups = (store.checkups || []).concat({ date: today(), good, total: L.q.length }).slice(-20); save(); }
      const label = good >= 7 ? L.strong : good >= 4 ? L.fair : L.risk;
      const color = good >= 7 ? 'var(--leaf)' : good >= 4 ? 'var(--marigold)' : 'var(--chilli)';
      const fixes = answers.map((a, i) => (a ? null : i)).filter((i) => i !== null);
      const summary = L.score + ': ' + good + '/' + L.q.length + ' (' + label + '). ' + (fixes.length ? L.fix + ': ' + fixes.map((i) => L.tip[i]).join(' ') : '');
      box.append(h('div', { class: 'card flat', style: { borderColor: color } },
        h('div', { class: 'row' }, h('h2', { style: { margin: 0 } }, L.score + ': ' + good + '/' + L.q.length + ' · ' + label), listenButton(() => [{ text: summary, lang }])),
        h('div', { class: 'meter', style: { margin: '10px 0' } }, h('i', { style: { width: good / L.q.length * 100 + '%', background: color } })),
        fixes.length ? h('div', {}, h('h3', {}, L.fix), h('ul', {}, fixes.map((i) => h('li', {}, L.tip[i])))) : null,
        h('button', { class: 'btn small ghost', type: 'button', onclick: () => { answers.fill(null); recorded = false; drawCheckup(); } }, L.restart)));
    }
  }
  drawCheckup();

  // ---------- I have been scammed ----------
  const stepsText = L.steps.map((s, i) => (i + 1) + '. ' + s).join(' ');
  page.append(h('div', { class: 'card stack' },
    h('div', { class: 'row' }, h('h2', { style: { margin: 0 } }, L.scam_title), listenButton(() => [{ text: L.scam_title + ' ' + stepsText, lang }])),
    h('ol', {}, L.steps.map((s) => h('li', { style: { marginBottom: '6px' } }, s))),
    h('div', { class: 'row' }, h('a', { class: 'btn', href: 'tel:1930' }, '📞 ' + L.helpline), h('a', { class: 'btn ghost', href: 'https://cybercrime.gov.in', target: '_blank', rel: 'noopener' }, L.portal))));

  // ---------- complaint summary builder ----------
  const sel = (opts) => h('select', { class: 'field' }, opts.map((o, i) => h('option', { value: String(i) }, o)));
  const type = sel(L.types), how = sel(L.hows);
  const amount = h('input', { class: 'field', type: 'text', inputmode: 'numeric', placeholder: '0' });
  const when = h('input', { class: 'field', type: 'text', placeholder: new Date().toLocaleString('en-IN') });
  const who = h('input', { class: 'field', type: 'text' });
  const story = h('textarea', { class: 'field', rows: '3' });
  const scamMsg = h('textarea', { class: 'field', rows: '3', maxlength: '5000', placeholder: 'Scam message (optional, for the evidence packet)' });
  const out = h('pre', { class: 'json hide', style: { whiteSpace: 'pre-wrap' } });
  const copy = h('button', { class: 'btn small ghost hide', type: 'button' }, L.copy);
  const lab = (text, el) => h('label', { class: 'lab' }, h('span', { class: 'small muted' }, text), el);
  const make = h('button', { class: 'btn', type: 'button', onclick: () => {
    const lines = ['CYBER FRAUD COMPLAINT SUMMARY', 'Type: ' + EN.types[+type.value], 'Amount lost: Rs ' + (amount.value || 'not stated'), 'Date and time: ' + (when.value || 'not stated'),
      'Payment method: ' + EN.hows[+how.value], 'Scammer details (phone / UPI ID / link): ' + (who.value || 'not known'), 'What happened: ' + (story.value || 'not stated'),
      'Request: please flag the transaction and the beneficiary account and take action as per procedure. Helpline reference: 1930.'];
    out.textContent = lines.join('\n'); out.classList.remove('hide'); copy.classList.remove('hide');
  } }, L.make);
  copy.addEventListener('click', async () => { try { await navigator.clipboard.writeText(out.textContent); toast(L.copied); } catch (e) { toast('Select the text and copy it.'); } });
  const evid = h('button', { class: 'btn scam', type: 'button', onclick: async () => {
    const payMap = ['upi', 'card', 'netbanking', 'cash'];
    (await import('../evidence.js')).openEvidence({ text: scamMsg.value, source: 'text', intent: 'unknown', qr: [] },
      { amount: amount.value, when: when.value, payment: payMap[+how.value], note: [EN.types[+type.value], who.value && ('Scammer: ' + who.value), story.value].filter(Boolean).join('. '), lost_money: !!amount.value });
  } }, '📄 ' + (store.lang === 'hi' ? 'हेल्पलाइन 1930 के लिए सबूत पैकेट बनाएँ' : store.lang === 'kn' ? '1930 ಗಾಗಿ ಸಾಕ್ಷ್ಯ ಪ್ಯಾಕೆಟ್ ರಚಿಸಿ' : 'Generate 1930 evidence packet'));
  page.append(h('div', { class: 'card stack' }, h('h2', {}, L.form_title),
    h('div', { class: 'grid cols-2' }, lab(L.f_type, type), lab(L.f_how, how), lab(L.f_amount, amount), lab(L.f_when, when)),
    lab(L.f_who, who), lab(L.f_story, story), lab('Scam message (optional)', scamMsg), h('div', { class: 'row' }, make, copy, evid), out, h('p', { class: 'small muted' }, L.note)));
}
