"""India-specific scam rules.

Each rule is a named pattern with an evidence weight (how strongly this wording suggests a scam), a plain-language
reason and a one-line tip. Rules cover English, Hinglish and a little Devanagari. A match that is preceded by
"do not / never / don't" is treated as a warning, not a request, so genuine bank alerts are not flagged.
"""
import re

F = re.I | re.S
GAP = r"(?:\w+\W+)"  # one word and the gap after it


def g(n, m=None):
    return GAP + "{0,%d}?" % n if m is None else GAP + "{%d,%d}?" % (n, m)


RULES = [
    dict(id="otp_ask", category="otp", weight=0.85, neg=True, title="Asks for your OTP, PIN or password",
         why="Banks and apps never ask you to share an OTP, PIN, CVV or password with anyone.",
         tip="Never tell anyone your OTP or PIN, not even someone who says they are from the bank.",
         patterns=[
             r"\b(?:share|send|tell|give|provide|forward|enter|submit|reply\W+with|read\W+out|confirm)\W+" + g(5) + r"(?:otp|pin|cvv|password|passcode|mpin|upi\W*pin|atm\W*pin)\b",
             r"\b(?:otp|pin|cvv|password|passcode|mpin)\W+" + g(4) + r"(?:to\W+(?:us|me|the\W+(?:executive|agent|officer))|on\W+(?:call|whatsapp))\b",
             r"\botp\W+(?:batao|bhejo|share\W+karo|dijiye|bataye|bataiye|bata\W+do)\b",
             r"ओटीपी\W+(?:बताएं|बताइए|शेयर|भेजें|दें)",
         ]),
    dict(id="upi_collect", category="upi", weight=0.85, neg=False, title="Tries to make you approve a payment",
         why="You never have to enter a PIN or approve a request to RECEIVE money. That step only sends money out.",
         tip="Receiving money never needs your PIN. If asked, it's a scam.",
         patterns=[
             r"\b(?:enter|put|type|use)\W+" + g(3) + r"(?:upi\W*)?pin\W+" + g(3) + r"(?:to\W+)?(?:receive|get|credit|claim)\b",
             r"\b(?:collect|payment|pending)\W+request\b.{0,60}\b(?:approve|accept|pin|pay)\b",
             r"\bscan\W+" + g(3) + r"(?:qr|code)\W+" + g(4) + r"(?:to\W+)?(?:receive|get|claim|refund|credit)\b",
             r"\b(?:approve|accept)\W+" + g(4) + r"(?:request|collect)\W+" + g(5) + r"(?:receive|refund|cashback|get)\b",
         ]),
    dict(id="fake_kyc", category="kyc", weight=0.7, neg=False, title="Fake KYC / account-update pressure",
         why="Banks do not ask you to update KYC through an SMS link or a phone number in a message.",
         tip="Update KYC only inside the official app or at your branch.",
         patterns=[
             r"\be?-?kyc\W+" + g(10) + r"(?:expire[ds]?|pending|incomplete|suspend\w*|block\w*|update\W+(?:now|today|immediately|within)|verify\W+now|deactivat\w+|not\W+(?:updated|completed))",
             r"\b(?:update|complete|verify|renew)\W+" + g(3) + r"(?:your\W+)?e?-?kyc\b",
             r"\b(?:pan|aadhaar|aadhar)\W+" + g(6) + r"(?:update|verif\w+|link\w*)\W+" + g(8) + r"(?:expire|block|suspend|today|now|within|immediately|urgent)",
             r"केवाईसी",
         ]),
    dict(id="account_threat", category="threat", weight=0.55, neg=False, ctx_skip=True, title="Threatens to block or close something",
         why="Scammers invent a threat (blocked, suspended, disconnected) so you panic and act before you think.",
         tip="Real services warn you inside their own app. Call the number on your card, not the one in the message.",
         patterns=[
             r"\b(?:account|card|sim|number|upi|wallet|service|connection|aadhaar|pan)\W+" + g(5) + r"(?:will\W+be|has\W+been|is\W+being|shall\W+be|gets?|is\W+going\W+to\W+be)\W+" + g(2) + r"(?:blocked|suspended|deactivated|disconnected|closed|frozen|terminated|cancelled|canceled|deleted)\b",
             r"\b(?:band|block|suspend)\W+ho\W+(?:jayega|jaega|jayegi|jaye)\b",
             r"\b(?:will|shall)\W+(?:be\W+)?(?:blocked|suspended|deactivated|disconnected)\W+" + g(6) + r"(?:today|tonight|tomorrow|hours?)\b",
         ]),
    dict(id="urgency", category="urgency", weight=0.35, neg=False, title="Rushes you to act",
         why="Pressure and deadlines are used to stop you from checking. Genuine messages rarely give you minutes to decide.",
         tip="Slow down. A real problem can wait while you verify it.",
         patterns=[
             r"\b(?:within|in)\W+(?:the\W+)?(?:next\W+)?\d+\W*(?:hours?|hrs?|minutes?|mins?)\b",
             r"\b(?:immediately|urgent(?:ly)?|right\W+now|asap|today\W+only|last\W+chance|final\W+(?:notice|warning|reminder)|act\W+now|expires?\W+(?:today|tonight)|before\W+midnight|hurry|limited\W+time)\b",
             r"\b(?:turant|fauran|jaldi|aaj\W+hi|abhi\W+(?:click|call|pay|update|verify))\b",
             r"(?:तुरंत|जल्दी|आज\W+ही)",
         ]),
    dict(id="prize", category="prize", weight=0.7, neg=False, title="Says you won something you never entered",
         why="You can't win a lottery or draw you never joined. Prize messages exist to collect a fee or your details.",
         tip="If you didn't enter, you didn't win.",
         patterns=[
             r"\byou(?:\W+(?:have|just|are|ve))?\W+(?:won|win|been\W+selected|are\W+(?:the\W+)?(?:lucky\W+)?winner)\b",
             r"\bcongratulations?\b.{0,50}\b(?:won|prize|reward|gift|winner|selected|lucky)\b",
             r"\b(?:lucky\W+draw|lottery|kbc|jackpot)\b",
             r"\bclaim\W+" + g(3) + r"(?:prize|reward|gift|cashback|bonus)\b",
             r"\b(?:reward|redeem)\W+points?\W+" + g(4) + r"(?:expire|expiring|lapse)\w*",
             r"\b(?:inaam|inam|lottery)\W+(?:jeeta|jeete|nikli|mila)\b",
         ]),
    dict(id="advance_fee", category="fee", weight=0.55, neg=False, title="Asks for a small fee before you receive anything",
         why="Asking you to pay first (registration, processing, customs, redelivery) is the oldest advance-fee trick.",
         tip="Real prizes, jobs and loans never ask you to pay money upfront.",
         patterns=[
             r"\b(?:pay|deposit|transfer|send)\W+" + g(4) + r"(?:small\W+)?(?:fee|charges?|registration|processing|deposit|(?:rs\.?|₹|inr)\W*\d[\d,]*)\W+" + g(8) + r"(?:to\W+)?(?:claim|release|receive|unlock|activate|process|confirm|join|get|clear|reschedule|deliver)\w*",
             r"\b(?:processing|registration|clearance|redelivery|customs|gst|insurance|refundable|security|activation)\W+(?:fee|charges?|deposit)\b",
         ]),
    dict(id="job_scam", category="job", weight=0.65, neg=False, title="Too-good-to-be-true job offer",
         why="Easy work-from-home pay for likes, ratings or simple tasks is a well-known fraud pattern.",
         tip="Genuine employers don't recruit over WhatsApp/Telegram or ask you to pay or do paid 'tasks'.",
         patterns=[
             r"\b(?:work\W+from\W+home|part\W*time\W+(?:job|work)|data\W+entry\W+job|task\W*based)\b.{0,100}\b(?:earn|income|salary|paid|payment|per\W+(?:day|hour)|daily|weekly)\b",
             r"\bearn\W+" + g(4) + r"(?:(?:rs\.?|₹|inr)\W*)?\d[\d,]*\W*(?:/|per|a|each)\W*(?:day|daily|hour|week)\b",
             r"\b(?:like|follow|subscribe|rate|review|watch)\W+" + g(8) + r"(?:earn|paid|payment|get\W+paid|commission)\b",
             r"\bdaily\W+(?:income|payout|salary|payment)\b",
             r"\bghar\W+baithe\W+(?:kamao|kamai|paise)\b",
             r"\bhiring\W+" + g(8) + r"(?:no\W+experience|freshers?)\W+" + g(10) + r"(?:whatsapp|telegram)\b",
         ]),
    dict(id="courier", category="courier", weight=0.5, neg=False, title="Fake parcel / delivery problem",
         why="Fake courier texts claim a parcel is stuck to get you to tap a link or pay a small fee.",
         tip="Check delivery only from the shop's own app or the courier's official site.",
         patterns=[
             r"\b(?:parcel|package|shipment|courier|consignment|delivery|order)\W+" + g(8) + r"(?:held|on\W+hold|stuck|failed|could\W+not\W+be\W+delivered|undelivered|returned|detained|seized|address\W+(?:is\W+)?(?:incomplete|incorrect|invalid)|reschedule|rescheduled)\b",
             r"\b(?:update|confirm|correct)\W+" + g(3) + r"(?:your\W+)?(?:delivery\W+)?address\b.{0,60}\b(?:parcel|package|delivery|courier)\b",
             r"\bcustoms\W+" + g(10) + r"(?:clearance|duty|fee|charge|parcel|package)\b",
         ]),
    dict(id="utility_threat", category="utility", weight=0.7, neg=False, title="Fake electricity/bill disconnection",
         why="'Your power will be cut tonight, call this officer' is a common scam. Utilities don't disconnect by SMS at night.",
         tip="Check your bill in the official app or on the utility's website.",
         patterns=[
             r"\b(?:electricity|power|bill|meter|gas|connection)\W+" + g(10) + r"(?:disconnect\w*|cut|discontinu\w+|terminat\w+)\b.{0,100}\b(?:tonight|today|\d{1,2}[:.]\d{2}|call|contact|officer|executive)\b",
         ]),
    dict(id="invest", category="invest", weight=0.65, neg=False, title="Guaranteed returns / investment tips",
         why="No genuine investment guarantees profit. 'Double your money' and VIP tip groups are used to steal deposits.",
         tip="If it promises a guaranteed profit, it's a scam. Check any advisor on the SEBI website.",
         patterns=[
             r"\b(?:guaranteed|assured|fixed)\W+(?:returns?|profits?|income)\b",
             r"\bdouble\W+(?:your\W+)?(?:money|investment)\b",
             r"\b\d{2,4}\W*%\W*(?:returns?|profits?|guaranteed)\b",
             r"\b(?:vip|premium|insider)\W+(?:group|signals?|tips?|channel)\b",
             r"\b(?:crypto|bitcoin|usdt|forex)\W+" + g(8) + r"(?:profit|returns?|earn|invest|doubl\w+)\b",
             r"\b(?:stock|share\W+market|trading)\W+(?:tips?|signals?|calls?|expert)\W+" + g(8) + r"(?:group|channel|join|whatsapp|telegram)\b",
         ]),
    dict(id="loan", category="loan", weight=0.6, neg=False, title="Instant loan with no checks",
         why="Genuine lenders check documents and credit history. 'No documents, instant approval' loans are bait.",
         tip="Borrow only from RBI-registered lenders, and never pay a fee to 'release' a loan.",
         patterns=[
             r"\b(?:instant|pre\W*approved|quick)\W+" + g(3) + r"loan\b",
             r"\bloan\W+" + g(8) + r"(?:no\W+(?:documents?|cibil|credit\W+check|collateral)|without\W+(?:documents?|cibil|income\W+proof)|approved\W+in\W+\d+\W*(?:minutes?|mins?))\b",
         ]),
    dict(id="authority", category="authority", weight=0.75, neg=False, title="Pretends to be police or a government agency",
         why="Calls or messages claiming a 'drug parcel', 'digital arrest' or legal case are scams. Agencies don't arrest or fine over chat.",
         tip="Hang up. No agency settles a case by video call or payment on the spot. Call 1930.",
         patterns=[
             r"\b(?:cbi|ncb|narcotics|customs|police|cyber\W*cell|enforcement\W+directorate|trai|income\W+tax\W+(?:dept|department|officer)|rbi)\b.{0,100}\b(?:parcel|drugs?|illegal|case|complaint|fir|money\W+laundering|suspend\w*|arrest\w*|summons|warrant|notice)\b",
             r"\bdigital\W+arrest\b",
             r"\byour\W+(?:aadhaar|aadhar|number)\W+(?:is|has\W+been)\W+(?:linked|used|involved)\b",
         ]),
    dict(id="tax_refund", category="refund", weight=0.6, neg=False, title="Refund bait",
         why="Scammers promise tax or payment refunds to get your bank details or PIN.",
         tip="Refunds are credited automatically. You never need to enter card details to receive one.",
         patterns=[
             r"\b(?:income\W+tax|it\W+dept|itr)\W+" + g(10) + r"refund\b.{0,100}\b(?:click|link|submit|claim|share|details|enter|call|verify|whatsapp)\b",
             r"\brefund\W+of\W+(?:rs\.?|₹|inr)?\W*[\d,]+\W+" + g(12) + r"(?:credit|claim|approved?|pending|click|link)\w*\b",
             r"\b(?:refund|cashback|reversal|compensation)\W+" + g(10) + r"(?:pending|initiated|approved)\W+" + g(12) + r"(?:click|link|share|scan|enter|call|pin|otp)\b",
         ]),
    dict(id="sim_upgrade", category="sim", weight=0.5, neg=False, title="Fake SIM block / upgrade",
         why="'Your SIM will be blocked' or 'upgrade to 5G' texts lead to link or OTP traps.",
         tip="Telecom operators don't block SIMs through random links. Check with your operator's app.",
         patterns=[
             r"\b(?:sim|mobile\W+number)\W+" + g(6) + r"(?:block\w*|deactivat\w+|expire[sd]?|disconnect\w*|suspend\w*|upgrade)\b",
             r"\bupgrade\W+" + g(3) + r"(?:to\W+)?(?:4g|5g)\W+(?:sim)?\b",
         ]),
    dict(id="remote_access", category="remote", weight=0.8, neg=True, title="Asks you to install a remote-control app",
         why="Apps like AnyDesk or TeamViewer let a stranger see and control your phone, including banking apps.",
         tip="Never install screen-sharing apps at a stranger's request.",
         patterns=[
             r"\b(?:anydesk|teamviewer|quick\W*support|rustdesk|ultraviewer|airdroid|screen\W*shar\w+)\b",
         ]),
    dict(id="apk", category="apk", weight=0.75, neg=False, title="Pushes you to install an app from a link",
         why="Apps installed from links (APK files) can read your messages and OTPs.",
         tip="Install apps only from the Play Store or App Store.",
         patterns=[
             r"\.apk\b",
             r"\b(?:download|install)\W+" + g(4) + r"(?:the\W+)?(?:apk|app)\W+" + g(5) + r"(?:link|below|here)\b",
         ]),
    dict(id="off_platform", category="offplatform", weight=0.3, neg=False, title="Moves you to WhatsApp or Telegram",
         why="Scammers move chats to private apps where there is no oversight.",
         tip="Be careful when an 'official' contact asks you to continue on WhatsApp or Telegram.",
         patterns=[
             r"\b(?:message|contact|text|dm|join|add)\W+" + g(5) + r"(?:on\W+)?(?:whatsapp|telegram|signal)\W+" + g(4) + r"(?:group|channel|link|number|\+?\d{10})\b",
             r"\b(?:wa\.me|t\.me)/",
         ]),
    dict(id="credential", category="credential", weight=0.6, neg=True, title="Asks for card or login details",
         why="No genuine company asks for your full card, net-banking login or ID numbers by message.",
         tip="Enter card details only on the checkout page of a site you opened yourself.",
         patterns=[
             r"\b(?:verify|confirm|update|enter|share|send)\W+" + g(5) + r"(?:card\W+(?:number|details)|net\W*banking|login\W+(?:id|credentials|details)|atm\W*pin|debit\W+card|credit\W+card\W+details|aadhaar\W+number|pan\W+(?:number|details))\b",
         ]),
    dict(id="family_impersonation", category="family", weight=0.65, neg=False, title="Pretends to be a relative in trouble",
         why="'Hi Mom, I lost my phone, this is my new number, send money' is a common impersonation scam.",
         tip="Call the relative on their old number or ask a question only they can answer before sending money.",
         patterns=[
             r"\b(?:hi|hello|hey)?\W*(?:mom|mum|mama|mummy|dad|papa|beta|bhaiya|didi|uncle|aunty)\b.{0,120}\b(?:new\W+number|lost\W+my\W+phone|phone\W+(?:is\W+)?(?:broken|damaged|lost|dead)|use\W+this\W+number)\b",
             r"\b(?:new\W+number|lost\W+my\W+phone|phone\W+(?:is\W+)?(?:broken|damaged|lost))\b.{0,160}\b(?:send|transfer|pay|gpay|upi)\b.{0,60}\b(?:urgent\w*|right\W+now|immediately|today)\b",
         ]),
    dict(id="gift_card", category="giftcard", weight=0.6, neg=False, title="Asks for gift cards or codes",
         why="Nobody legitimate asks you to pay with gift cards or voucher codes.",
         tip="Gift cards are not a payment method for bills, taxes or jobs.",
         patterns=[r"\b(?:gift\W+card|google\W+play\W+(?:code|card)|itunes\W+card|amazon\W+pay\W+(?:card|voucher))\b"]),
    dict(id="secrecy", category="secrecy", weight=0.6, neg=False, title="Tells you to keep it secret",
         why="Scammers isolate you so family or the bank can't warn you.",
         tip="Any request to 'tell no one' is a red flag. Talk to someone you trust.",
         patterns=[
             r"\b(?:do\W+not|don'?t|never)\W+" + g(3) + r"(?:tell|inform|discuss|share\W+with)\W+" + g(4) + r"(?:anyone|family|your\W+(?:bank|family)|police)\b.{0,0}",
             r"\bkeep\W+(?:this|it)\W+(?:confidential|secret|private)\b",
         ]),
    dict(id="guarantee", category="prize", weight=0.4, neg=False, title="Over-the-top promises",
         why="'100% guaranteed' and 'risk-free' are things honest offers avoid.",
         tip="If it sounds too good to be true, it is.",
         patterns=[r"\b100\W*%\W*(?:guaranteed|safe|genuine|legit|secure|profit)\b", r"\brisk\W*free\b", r"\bno\W+risk\b"]),
    dict(id="contact_number", category="link", weight=0.35, neg=False, title="Pushes you to call a number in the message",
         why="Scam texts often give a mobile number to call. A real bank's number is on the back of your card.",
         tip="Look up the official number yourself; don't trust the one in the message.",
         patterns=[r"\b(?:call|contact|whatsapp|ring|dial)\W+" + g(5) + r"(?:on|at|:)?\W*(?:\+?91[\s-]?)?[6-9]\d{9}\b"]),
    dict(id="click_link", category="link", weight=0.3, neg=False, title="Tells you to tap a link",
         why="Links in unexpected messages are the main way phishing works.",
         tip="Don't tap links in unexpected messages. Open the app or type the website yourself.",
         patterns=[
             r"\b(?:click|tap|open|visit|follow|login|log\W+in|sign\W+in)\W+" + g(4) + r"(?:the\W+)?(?:link|below|here|url)\b",
             r"\b(?:link\W+(?:par|pe)\W+)?(?:click|tap)\W+(?:karein|kare|karo|kijiye)\b",
         ]),
]

# Wording that matches normal, genuine messages. It only lowers suspicion when no strong scam rule fired.
SAFE_RULES = [
    dict(id="otp_notice", weight=0.2, title="Standard OTP notice",
         why="This warns you NOT to share the code, which is what genuine banks do.",
         patterns=[r"\b(?:do\W+not|don'?t|never)\W+share\W+" + g(4) + r"(?:otp|pin|code|password|cvv)\b",
                   r"\bis\W+(?:your|the)\W+(?:otp|one\W*time\W+(?:password|pin)|verification\W+code)\b"]),
    dict(id="txn_alert", weight=0.15, title="Normal transaction alert format",
         why="Plain debit/credit alerts with no link and no request are what banks really send.",
         patterns=[r"\b(?:debited|credited)\W+" + g(8) + r"(?:a/?c|account|ac|upi|ref|txn)\b",
                   r"\b(?:avl|available)\W+bal"]),
]

_BENIGN_CTX = re.compile(r"(?:as\s+requested|as\s+per\s+your\s+request|at\s+your\s+request|you\s+requested|requested\s+by\s+you|on\s+your\s+request)", re.I)
_NEG_RE = re.compile(r"(?:do\s+not|don'?t|dont|never|should\s+not|shouldn'?t|mat\s|kabhi\s+nahi|beware|warning)\W+(?:\w+\W+){0,8}$", re.I)

COMPILED = []
for r in RULES:
    COMPILED.append((r, [re.compile(p, F) for p in r["patterns"]]))
SAFE_COMPILED = [(r, [re.compile(p, F) for p in r["patterns"]]) for r in SAFE_RULES]


def _negated(text, start):
    return bool(_NEG_RE.search(text[max(0, start - 70):start]))


def run_rules(norm):
    """Apply all rules to normalised text. Returns (hits, safe_hits). Each hit has spans in normalised coordinates."""
    text = norm.text
    hits = []
    for rule, pats in COMPILED:
        spans = []
        for rx in pats:
            for m in rx.finditer(text):
                if rule["neg"] and _negated(text, m.start()):
                    continue
                if rule.get("ctx_skip") and _BENIGN_CTX.search(text[max(0, m.start() - 80):m.end() + 40]):
                    continue
                spans.append((m.start(), m.end()))
        if spans:
            hits.append({"id": rule["id"], "category": rule["category"], "weight": rule["weight"], "title": rule["title"],
                         "why": rule["why"], "tip": rule["tip"], "spans": spans[:3]})
    safe = []
    for rule, pats in SAFE_COMPILED:
        spans = [(m.start(), m.end()) for rx in pats for m in rx.finditer(text)]
        if spans:
            safe.append({"id": rule["id"], "weight": rule["weight"], "title": rule["title"], "why": rule["why"], "spans": spans[:2]})
    return hits, safe


def rule_score(hits):
    """Noisy-OR over rule weights: several independent warning signs add up, but one weak sign stays weak."""
    miss = 1.0
    for h in hits:
        miss *= (1 - h["weight"] * 0.95)
    return min(0.98, 1 - miss)
