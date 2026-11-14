// Text for the account page. NOTE: Hindi and Kannada need a native-speaker review. Server error messages are English.
import { store } from './store.js';

const A = {
  en: {
    nav: 'Log in', title: 'Your account', sub: 'Optional. Save your progress, badges and security-checkup scores so they follow you to any device. Pasted messages are never saved.',
    tab_login: 'Log in', tab_create: 'Create account', username: 'Username', username_hint: '3 to 30 characters: letters, numbers, dot or underscore', display: 'Name (optional)', password: 'Password', password_hint: 'At least 8 characters', confirm: 'Confirm password', mismatch: 'Passwords do not match.',
    login_btn: 'Log in', create_btn: 'Create account', keeps: 'Your progress on this device will be saved to the account.', working: 'Please wait…',
    forgot: 'Forgot your password?', reset_title: 'Reset with your recovery code', recovery: 'Recovery code', new_password: 'New password', reset_btn: 'Reset password', reset_done: 'Password changed. Save your NEW recovery code:',
    rc_title: 'Save your recovery code', rc_body: 'This is the only way to reset your password, because we do not ask for an email. It is shown once. Keep it somewhere safe.', rc_copy: 'Copy', rc_download: 'Download', rc_saved: 'I have saved my recovery code', rc_continue: 'Continue',
    hi_user: 'Hi', member_since: 'Member since', sync_local: 'On this device only', sync_saving: 'Saving…', sync_saved: 'Saved to your account', sync_error: 'Could not save. Will retry.',
    data_title: 'What we store', data_body: 'Your username, display name, a scrypt hash of your password, and your progress (XP, badges, streak, language, checkup scores). We do not store pasted messages, emails or phone numbers.',
    download: 'Download my data', logout: 'Log out', change_pw: 'Change password', current_pw: 'Current password', save_pw: 'Save new password', pw_changed: 'Password changed. Other devices were signed out.',
    delete_title: 'Delete account', delete_body: 'Deletes your account and saved progress from the server. This cannot be undone.', delete_btn: 'Delete my account', delete_confirm: 'Enter your password to confirm', deleted: 'Account deleted.',
    priv_title: 'Privacy and community', save_history: 'Save my scan history (verdict and scam type only, never the message)', leaderboard_opt: 'Show me on the leaderboard (display name and XP)', history_title: 'Your recent scans', history_empty: 'Nothing saved yet.', clear_history: 'Clear history', lb_title: 'Leaderboard', lb_note: 'Only players who opted in appear. Scores are reported by the browser, so the board is for fun.',
    guest_note: 'You are playing as a guest. Your progress stays on this device.', copied: 'Copied',
  },
  hi: {
    nav: 'लॉग इन', title: 'आपका खाता', sub: 'वैकल्पिक। अपनी प्रगति, बैज और सुरक्षा-चेकअप स्कोर सेव करें ताकि वे हर डिवाइस पर मिलें। चिपकाए गए मैसेज कभी सेव नहीं होते।',
    tab_login: 'लॉग इन', tab_create: 'खाता बनाएँ', username: 'यूज़रनेम', username_hint: '3 से 30 अक्षर: अक्षर, संख्या, डॉट या अंडरस्कोर', display: 'नाम (वैकल्पिक)', password: 'पासवर्ड', password_hint: 'कम से कम 8 अक्षर', confirm: 'पासवर्ड दोबारा लिखें', mismatch: 'पासवर्ड मेल नहीं खाते।',
    login_btn: 'लॉग इन करें', create_btn: 'खाता बनाएँ', keeps: 'इस डिवाइस की प्रगति खाते में सेव हो जाएगी।', working: 'कृपया रुकें…',
    forgot: 'पासवर्ड भूल गए?', reset_title: 'रिकवरी कोड से रीसेट करें', recovery: 'रिकवरी कोड', new_password: 'नया पासवर्ड', reset_btn: 'पासवर्ड रीसेट करें', reset_done: 'पासवर्ड बदल गया। अपना नया रिकवरी कोड सेव करें:',
    rc_title: 'अपना रिकवरी कोड सेव करें', rc_body: 'हम ईमेल नहीं माँगते, इसलिए पासवर्ड रीसेट करने का यही एकमात्र तरीका है। यह सिर्फ़ एक बार दिखता है। इसे सुरक्षित रखें।', rc_copy: 'कॉपी करें', rc_download: 'डाउनलोड करें', rc_saved: 'मैंने अपना रिकवरी कोड सेव कर लिया है', rc_continue: 'आगे बढ़ें',
    hi_user: 'नमस्ते', member_since: 'सदस्य बने', sync_local: 'सिर्फ़ इस डिवाइस पर', sync_saving: 'सेव हो रहा है…', sync_saved: 'आपके खाते में सेव है', sync_error: 'सेव नहीं हो सका। फिर कोशिश होगी।',
    data_title: 'हम क्या सेव करते हैं', data_body: 'आपका यूज़रनेम, नाम, पासवर्ड का scrypt हैश, और आपकी प्रगति (XP, बैज, स्ट्रीक, भाषा, चेकअप स्कोर)। हम चिपकाए गए मैसेज, ईमेल या फ़ोन नंबर सेव नहीं करते।',
    download: 'मेरा डेटा डाउनलोड करें', logout: 'लॉग आउट', change_pw: 'पासवर्ड बदलें', current_pw: 'मौजूदा पासवर्ड', save_pw: 'नया पासवर्ड सेव करें', pw_changed: 'पासवर्ड बदल गया। दूसरे डिवाइस से लॉग आउट कर दिया गया।',
    delete_title: 'खाता हटाएँ', delete_body: 'सर्वर से आपका खाता और सेव की हुई प्रगति हटा दी जाती है। इसे वापस नहीं किया जा सकता।', delete_btn: 'मेरा खाता हटाएँ', delete_confirm: 'पुष्टि के लिए अपना पासवर्ड लिखें', deleted: 'खाता हटा दिया गया।',
    priv_title: 'गोपनीयता और समुदाय', save_history: 'मेरी स्कैन हिस्ट्री सेव करें (सिर्फ़ नतीजा और स्कैम का प्रकार, मैसेज कभी नहीं)', leaderboard_opt: 'मुझे लीडरबोर्ड पर दिखाएँ (नाम और XP)', history_title: 'आपके हाल के स्कैन', history_empty: 'अभी कुछ सेव नहीं है।', clear_history: 'हिस्ट्री मिटाएँ', lb_title: 'लीडरबोर्ड', lb_note: 'सिर्फ़ वही खिलाड़ी दिखते हैं जिन्होंने चुना है। स्कोर ब्राउज़र से आते हैं, इसलिए यह मज़े के लिए है।',
    guest_note: 'आप अतिथि के रूप में खेल रहे हैं। प्रगति इसी डिवाइस पर रहती है।', copied: 'कॉपी हो गया',
  },
  kn: {
    nav: 'ಲಾಗಿನ್', title: 'ನಿಮ್ಮ ಖಾತೆ', sub: 'ಐಚ್ಛಿಕ. ನಿಮ್ಮ ಪ್ರಗತಿ, ಬ್ಯಾಡ್ಜ್ ಮತ್ತು ಭದ್ರತಾ ತಪಾಸಣೆ ಅಂಕಗಳನ್ನು ಉಳಿಸಿ, ಯಾವುದೇ ಸಾಧನದಲ್ಲಿ ಸಿಗುತ್ತವೆ. ಅಂಟಿಸಿದ ಸಂದೇಶಗಳನ್ನು ಎಂದಿಗೂ ಉಳಿಸುವುದಿಲ್ಲ.',
    tab_login: 'ಲಾಗಿನ್', tab_create: 'ಖಾತೆ ರಚಿಸಿ', username: 'ಬಳಕೆದಾರ ಹೆಸರು', username_hint: '3 ರಿಂದ 30 ಅಕ್ಷರ: ಅಕ್ಷರ, ಸಂಖ್ಯೆ, ಡಾಟ್ ಅಥವಾ ಅಂಡರ್ ಸ್ಕೋರ್', display: 'ಹೆಸರು (ಐಚ್ಛಿಕ)', password: 'ಪಾಸ್ ವರ್ಡ್', password_hint: 'ಕನಿಷ್ಠ 8 ಅಕ್ಷರ', confirm: 'ಪಾಸ್ ವರ್ಡ್ ಮತ್ತೆ ಬರೆಯಿರಿ', mismatch: 'ಪಾಸ್ ವರ್ಡ್ ಹೊಂದಿಕೆಯಾಗುತ್ತಿಲ್ಲ.',
    login_btn: 'ಲಾಗಿನ್ ಮಾಡಿ', create_btn: 'ಖಾತೆ ರಚಿಸಿ', keeps: 'ಈ ಸಾಧನದ ಪ್ರಗತಿ ಖಾತೆಗೆ ಉಳಿಸಲಾಗುತ್ತದೆ.', working: 'ದಯವಿಟ್ಟು ಕಾಯಿರಿ…',
    forgot: 'ಪಾಸ್ ವರ್ಡ್ ಮರೆತಿರಾ?', reset_title: 'ರಿಕವರಿ ಕೋಡ್ ಮೂಲಕ ಮರುಹೊಂದಿಸಿ', recovery: 'ರಿಕವರಿ ಕೋಡ್', new_password: 'ಹೊಸ ಪಾಸ್ ವರ್ಡ್', reset_btn: 'ಪಾಸ್ ವರ್ಡ್ ಮರುಹೊಂದಿಸಿ', reset_done: 'ಪಾಸ್ ವರ್ಡ್ ಬದಲಾಗಿದೆ. ನಿಮ್ಮ ಹೊಸ ರಿಕವರಿ ಕೋಡ್ ಉಳಿಸಿ:',
    rc_title: 'ನಿಮ್ಮ ರಿಕವರಿ ಕೋಡ್ ಉಳಿಸಿ', rc_body: 'ನಾವು ಇಮೇಲ್ ಕೇಳುವುದಿಲ್ಲ, ಆದ್ದರಿಂದ ಪಾಸ್ ವರ್ಡ್ ಮರುಹೊಂದಿಸಲು ಇದೊಂದೇ ದಾರಿ. ಇದು ಒಮ್ಮೆ ಮಾತ್ರ ತೋರಿಸಲಾಗುತ್ತದೆ. ಸುರಕ್ಷಿತವಾಗಿಡಿ.', rc_copy: 'ನಕಲಿಸಿ', rc_download: 'ಡೌನ್ ಲೋಡ್', rc_saved: 'ನಾನು ನನ್ನ ರಿಕವರಿ ಕೋಡ್ ಉಳಿಸಿದ್ದೇನೆ', rc_continue: 'ಮುಂದುವರಿಸಿ',
    hi_user: 'ನಮಸ್ಕಾರ', member_since: 'ಸದಸ್ಯರಾದ ದಿನ', sync_local: 'ಈ ಸಾಧನದಲ್ಲಿ ಮಾತ್ರ', sync_saving: 'ಉಳಿಸಲಾಗುತ್ತಿದೆ…', sync_saved: 'ನಿಮ್ಮ ಖಾತೆಗೆ ಉಳಿಸಲಾಗಿದೆ', sync_error: 'ಉಳಿಸಲು ಆಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಲಾಗುವುದು.',
    data_title: 'ನಾವು ಏನನ್ನು ಉಳಿಸುತ್ತೇವೆ', data_body: 'ನಿಮ್ಮ ಬಳಕೆದಾರ ಹೆಸರು, ಹೆಸರು, ಪಾಸ್ ವರ್ಡ್ ನ scrypt ಹ್ಯಾಶ್ ಮತ್ತು ನಿಮ್ಮ ಪ್ರಗತಿ (XP, ಬ್ಯಾಡ್ಜ್, ಸತತ ದಿನ, ಭಾಷೆ, ತಪಾಸಣೆ ಅಂಕ). ಅಂಟಿಸಿದ ಸಂದೇಶ, ಇಮೇಲ್ ಅಥವಾ ಫೋನ್ ಸಂಖ್ಯೆ ಉಳಿಸುವುದಿಲ್ಲ.',
    download: 'ನನ್ನ ಡೇಟಾ ಡೌನ್ ಲೋಡ್ ಮಾಡಿ', logout: 'ಲಾಗ್ ಔಟ್', change_pw: 'ಪಾಸ್ ವರ್ಡ್ ಬದಲಿಸಿ', current_pw: 'ಈಗಿನ ಪಾಸ್ ವರ್ಡ್', save_pw: 'ಹೊಸ ಪಾಸ್ ವರ್ಡ್ ಉಳಿಸಿ', pw_changed: 'ಪಾಸ್ ವರ್ಡ್ ಬದಲಾಗಿದೆ. ಇತರ ಸಾಧನಗಳಿಂದ ಲಾಗ್ ಔಟ್ ಮಾಡಲಾಗಿದೆ.',
    delete_title: 'ಖಾತೆ ಅಳಿಸಿ', delete_body: 'ಸರ್ವರ್ ನಿಂದ ನಿಮ್ಮ ಖಾತೆ ಮತ್ತು ಉಳಿಸಿದ ಪ್ರಗತಿಯನ್ನು ಅಳಿಸುತ್ತದೆ. ಇದನ್ನು ಹಿಂತಿರುಗಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ.', delete_btn: 'ನನ್ನ ಖಾತೆ ಅಳಿಸಿ', delete_confirm: 'ದೃಢೀಕರಿಸಲು ನಿಮ್ಮ ಪಾಸ್ ವರ್ಡ್ ಬರೆಯಿರಿ', deleted: 'ಖಾತೆ ಅಳಿಸಲಾಗಿದೆ.',
    priv_title: 'ಗೌಪ್ಯತೆ ಮತ್ತು ಸಮುದಾಯ', save_history: 'ನನ್ನ ಸ್ಕ್ಯಾನ್ ಇತಿಹಾಸ ಉಳಿಸಿ (ಫಲಿತಾಂಶ ಮತ್ತು ವಂಚನೆಯ ಪ್ರಕಾರ ಮಾತ್ರ, ಸಂದೇಶ ಎಂದಿಗೂ ಅಲ್ಲ)', leaderboard_opt: 'ನನ್ನನ್ನು ಲೀಡರ್ ಬೋರ್ಡ್ ನಲ್ಲಿ ತೋರಿಸಿ (ಹೆಸರು ಮತ್ತು XP)', history_title: 'ನಿಮ್ಮ ಇತ್ತೀಚಿನ ಸ್ಕ್ಯಾನ್ ಗಳು', history_empty: 'ಇನ್ನೂ ಏನೂ ಉಳಿಸಿಲ್ಲ.', clear_history: 'ಇತಿಹಾಸ ಅಳಿಸಿ', lb_title: 'ಲೀಡರ್ ಬೋರ್ಡ್', lb_note: 'ಆಯ್ಕೆ ಮಾಡಿದ ಆಟಗಾರರು ಮಾತ್ರ ಕಾಣಿಸುತ್ತಾರೆ. ಅಂಕಗಳು ಬ್ರೌಸರ್ ನಿಂದ ಬರುತ್ತವೆ, ಆದ್ದರಿಂದ ಇದು ಮನರಂಜನೆಗಾಗಿ.',
    guest_note: 'ನೀವು ಅತಿಥಿಯಾಗಿ ಆಡುತ್ತಿದ್ದೀರಿ. ಪ್ರಗತಿ ಈ ಸಾಧನದಲ್ಲೇ ಇರುತ್ತದೆ.', copied: 'ನಕಲಿಸಲಾಗಿದೆ',
  },
};
export const at = (k) => (A[store.lang] && A[store.lang][k]) || A.en[k] || k;
