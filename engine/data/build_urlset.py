"""Standalone link benchmark: phishing URLs vs genuine URLs, written by hand. Used to measure the link analyzer alone.
Genuine URLs include sites that are NOT in our brand list, to show how the analyzer treats unfamiliar but honest domains."""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))

PHISH = [
 ("lookalike-brand", "http://sbi-kyc-update.xyz/login"), ("lookalike-brand", "https://hdfcbank-secure-login.top/netbanking"),
 ("lookalike-brand", "http://icici-kyc-verify.click/pan"), ("subdomain-decoy", "https://secure.hdfcbank.com.verify-now.top/kyc"),
 ("subdomain-decoy", "https://www.amazon.in.deals-today.top/offer"), ("typosquat", "paytrn.com/refund"), ("typosquat", "https://arnazon-india.shop/claim"),
 ("typosquat", "https://g00gle-support.top/recover"), ("lookalike-brand", "https://phonepe-rewards.live/claim"), ("ip-host", "http://192.168.4.7/pay"),
 ("ip-host", "http://45.33.12.9/sbi/login"), ("punycode", "https://xn--sbi-kyc-9ya.com/login"), ("at-sign", "http://sbi.co.in@evil-login.top/x"),
 ("lookalike-brand", "https://flipkart-offers.buzz/win"), ("free-hosting", "https://sbi-help.weebly.com/"), ("free-hosting", "https://hdfc-kyc-update.web.app/"),
 ("free-hosting", "https://paytm-offers.github.io/claim"), ("lookalike-brand", "https://axisbank-reward-points.cfd/redeem"), ("lookalike-brand", "https://uidai-aadhaar-update.xyz/verify"),
 ("lookalike-brand", "https://incometax-refund.top/claim"), ("lookalike-brand", "https://epfo-claim-online.shop/login"), ("lookalike-brand", "http://irctc-ticket-refund.click/pay"),
 ("lookalike-brand", "https://indiapost-reship.xyz/track"), ("lookalike-brand", "https://dtdc-address-fix.top/u"), ("lookalike-brand", "https://bluedart-redelivery.live/pay"),
 ("apk", "http://sbi-rewards.xyz/SBI_Rewards.apk"), ("apk", "https://rto-challan.top/app.apk"), ("lookalike-brand", "https://netflix-billing-update.top/pay"),
 ("lookalike-brand", "https://whatsapp-verify.click/continue"), ("lookalike-brand", "https://appleid-unlock.shop/verify"), ("lookalike-brand", "https://kotak-secure-login.buzz/"),
 ("lookalike-brand", "https://pnb-secure-kyc.click/"), ("lookalike-brand", "https://yesbank-netbanking-login.vip/"),
 ("unknown-brand", "https://amzn-gift.top/claim"), ("lookalike-brand", "https://jio-recharge-offer.xyz/free"), ("lookalike-brand", "https://swiggy-cashback.online/claim"),
 ("lookalike-brand", "https://zomato-gold-free.site/"), ("lookalike-brand", "https://microsoft-support-alert.top/"),
 ("shortener", "https://bit.ly/3xYzAb"), ("shortener", "https://tinyurl.com/sbi-kyc-now"), ("shortener", "https://cutt.ly/hdfcUpdate"), ("shortener", "https://t.ly/kycNow"),
 ("generic-bait", "https://login-verify-account.xyz/secure"), ("generic-bait", "https://pay-secure-wallet.top/upi"), ("generic-bait", "https://secure-bank-update.click/login"),
]
GENUINE = [
 ("official", u) for u in [
  "https://www.sbi.co.in/web/personal-banking", "https://www.hdfcbank.com/personal/pay/cards", "https://www.icicibank.com/", "https://www.axisbank.com/",
  "https://paytm.com/recharge", "https://www.phonepe.com/", "https://www.amazon.in/dp/B09XYZ", "https://www.flipkart.com/", "https://www.irctc.co.in/nget/train-search",
  "https://uidai.gov.in/en/", "https://www.incometax.gov.in/iec/foportal/", "https://www.npci.org.in/", "https://www.indiapost.gov.in/", "https://www.dtdc.in/tracking",
  "https://www.bluedart.com/tracking", "https://myaadhaar.uidai.gov.in/", "https://www.swiggy.com/restaurants", "https://www.zomato.com/", "https://www.jio.com/",
  "https://www.airtel.in/", "https://meet.google.com/abc-defg-hij", "https://pay.google.com/", "https://www.netflix.com/browse", "https://www.microsoft.com/en-in",
  "https://web.whatsapp.com/", "https://www.epfindia.gov.in/"]
] + [
 ("unfamiliar-genuine", u) for u in [
  "https://en.wikipedia.org/wiki/Phishing", "https://github.com/torvalds/linux", "https://zoom.us/j/123456789", "https://www.thehindu.com/news/", "https://www.ndtv.com/",
  "https://stackoverflow.com/questions", "https://www.linkedin.com/in/someone", "https://www.canva.com/", "https://www.zerodha.com/", "https://groww.in/stocks",
  "https://www.nseindia.com/", "https://razorpay.com/", "https://www.coursera.org/", "https://abc.xyz/", "https://www.mygov.in/", "https://www.digilocker.gov.in/",
  "https://bescom.karnataka.gov.in/", "https://www.bbc.com/news", "https://medium.com/@someone", "https://www.spotify.com/in/", "https://notion.so/workspace",
  "https://news.ycombinator.com/", "https://www.nytimes.com/"]
]

if __name__ == "__main__":
    path = os.path.join(HERE, "url_testset.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["url", "label", "kind"])
        for k, u in PHISH: w.writerow([u, 1, k])
        for k, u in GENUINE: w.writerow([u, 0, k])
    print("url set: %d phishing, %d genuine -> %s" % (len(PHISH), len(GENUINE), path))
