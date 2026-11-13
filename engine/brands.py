"""Brand and domain knowledge used by the link analyzer.

Official domains listed here are ones we are confident about. The list is deliberately short and easy to
extend: add a brand and its real registered domains and the lookalike checks pick it up automatically.
"""

# brand -> (keywords that appear in impersonating domains, official registered domains)
BRANDS = {
    "SBI": (["sbi", "onlinesbi", "yonosbi", "statebank"], ["sbi.co.in", "onlinesbi.sbi", "onlinesbi.com", "sbicard.com", "yonosbi.com"]),
    "HDFC Bank": (["hdfc", "hdfcbank"], ["hdfcbank.com", "hdfc.com", "hdfclife.com"]),
    "ICICI Bank": (["icici", "icicibank"], ["icicibank.com", "icicilombard.com", "iciciprulife.com"]),
    "Axis Bank": (["axisbank", "axis"], ["axisbank.com"]),
    "Kotak": (["kotak"], ["kotak.com"]),
    "PNB": (["pnbindia", "netpnb", "pnb"], ["pnbindia.in", "netpnb.com"]),
    "Bank of Baroda": (["bankofbaroda", "bobibanking"], ["bankofbaroda.in", "bankofbaroda.com"]),
    "Canara Bank": (["canarabank"], ["canarabank.com"]),
    "IDFC First": (["idfcfirstbank", "idfcbank"], ["idfcfirstbank.com"]),
    "Yes Bank": (["yesbank"], ["yesbank.in"]),
    "Union Bank": (["unionbank", "unionbankofindia"], ["unionbankofindia.co.in"]),
    "Bank of India": (["bankofindia"], ["bankofindia.co.in"]),
    "IndusInd": (["indusind", "indusindbank"], ["indusind.com"]),
    "Federal Bank": (["federalbank"], ["federalbank.co.in"]),
    "RBL Bank": (["rblbank"], ["rblbank.com"]),
    "AU Small Finance Bank": (["aubank"], ["aubank.in"]),
    "Indian Bank": (["indianbank"], ["indianbank.in"]),
    "IDBI Bank": (["idbibank"], ["idbibank.in"]),
    "BHIM": (["bhim", "bhimupi"], ["bhimupi.org.in"]),
    "MobiKwik": (["mobikwik"], ["mobikwik.com"]),
    "Freecharge": (["freecharge"], ["freecharge.in"]),
    "Paytm": (["paytm", "paytmbank"], ["paytm.com", "paytmbank.com"]),
    "PhonePe": (["phonepe"], ["phonepe.com"]),
    "Google": (["google", "gpay"], ["google.com", "google.co.in", "gpay.app.goo.gl"]),
    "Amazon": (["amazon"], ["amazon.in", "amazon.com", "amazon.co.uk"]),
    "Flipkart": (["flipkart"], ["flipkart.com"]),
    "Swiggy": (["swiggy"], ["swiggy.com"]),
    "Zomato": (["zomato"], ["zomato.com"]),
    "IRCTC": (["irctc"], ["irctc.co.in"]),
    "Aadhaar / UIDAI": (["uidai", "aadhaar", "aadhar"], ["uidai.gov.in"]),
    "Income Tax Dept": (["incometax", "incometaxindia"], ["incometax.gov.in", "incometaxindia.gov.in"]),
    "NPCI / UPI": (["npci", "bhimupi"], ["npci.org.in"]),
    "EPFO": (["epfo", "epfindia"], ["epfindia.gov.in", "epfo.gov.in"]),
    "India Post": (["indiapost"], ["indiapost.gov.in"]),
    "DTDC": (["dtdc"], ["dtdc.in", "dtdc.com"]),
    "Blue Dart": (["bluedart"], ["bluedart.com"]),
    "Delhivery": (["delhivery"], ["delhivery.com"]),
    "FedEx": (["fedex"], ["fedex.com"]),
    "DHL": (["dhl"], ["dhl.com"]),
    "Jio": (["jio", "myjio"], ["jio.com", "jiomart.com"]),
    "Airtel": (["airtel"], ["airtel.in", "airtel.com"]),
    "Vi (Vodafone Idea)": (["myvi", "vodafoneidea"], ["myvi.in", "vodafoneidea.com"]),
    "BSNL": (["bsnl"], ["bsnl.co.in"]),
    "WhatsApp": (["whatsapp"], ["whatsapp.com", "wa.me"]),
    "Telegram": (["telegram"], ["telegram.org", "t.me"]),
    "Netflix": (["netflix"], ["netflix.com"]),
    "Microsoft": (["microsoft"], ["microsoft.com", "live.com", "office.com"]),
    "Apple": (["apple", "icloud"], ["apple.com", "icloud.com"]),
    "Facebook / Instagram": (["facebook", "instagram"], ["facebook.com", "instagram.com"]),
}

OFFICIAL_ALL = {d for _, (_, doms) in BRANDS.items() for d in doms}
KEYWORD_TO_BRAND = {k: b for b, (kws, _) in BRANDS.items() for k in kws}
BRAND_OFFICIAL = {b: doms for b, (_, doms) in BRANDS.items()}

# Registered-domain suffixes made of two labels (so "sbi.co.in" is the registered domain, not "co.in").
MULTI_SUFFIX = {
    "co.in", "org.in", "net.in", "gov.in", "nic.in", "ac.in", "edu.in", "res.in", "gen.in", "firm.in", "ind.in",
    "co.uk", "org.uk", "gov.uk", "com.au", "co.za", "com.br", "co.jp", "com.sg", "com.cn", "co.nz", "com.pk",
}
TRUSTED_SUFFIXES = ("gov.in", "nic.in", "edu.in", "ac.in")

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "rb.gy", "cutt.ly", "is.gd", "tiny.cc", "shorturl.at", "ow.ly", "t.ly",
    "bitly.ws", "rebrand.ly", "shorturl.asia", "s.id", "v.gd", "lnkd.in",
}

SUSPICIOUS_TLDS = {
    "xyz", "top", "click", "link", "live", "icu", "vip", "buzz", "work", "support", "cfd", "sbs", "rest", "monster",
    "tk", "ml", "ga", "cf", "gq", "cc", "ws", "pw", "club", "fun", "life", "today", "cyou", "bar", "bond", "site",
    "online", "shop", "store", "website", "help", "services", "digital", "info", "biz",
}

FREE_HOSTING = {
    "weebly.com", "blogspot.com", "firebaseapp.com", "web.app", "github.io", "pages.dev", "vercel.app", "netlify.app",
    "glitch.me", "000webhostapp.com", "wixsite.com", "godaddysites.com", "webflow.io", "herokuapp.com", "onrender.com",
    "carrd.co", "sites.google.com", "forms.gle", "notion.site",
}

PATH_WORDS = ("login", "signin", "verify", "verification", "kyc", "update", "secure", "claim", "reward", "bonus",
              "refund", "otp", "unlock", "reactivate", "confirm", "pay", "upi", "redeem", "gift", "prize")

TLD_LIST = (
    "com|in|net|org|co|io|info|biz|xyz|top|click|link|live|online|site|shop|store|icu|vip|buzz|work|support|cfd|sbs|"
    "rest|monster|app|dev|me|us|uk|tk|ml|ga|cf|gq|cc|ws|pw|club|fun|life|today|world|website|tech|pro|cyou|bar|bond|"
    "digital|services|help|gov|edu|ru|cn|ly|gl|sh|page|gle"
)
