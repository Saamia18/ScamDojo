"""Builds the seed training set for the text classifier from hand-written message templates.

IMPORTANT: this is a SEED dataset written by the team for development. It is template-based, so it is much
cleaner than real SMS traffic. Replace or extend it with real public data (for example the UCI SMS Spam Collection)
and your own hand-labelled messages: put extra rows in engine/data/extra_train.csv (columns: text,label) and run
`python -m engine.train`.

Each template has an id. The train/test split is done BY TEMPLATE, so the model is always tested on message
patterns it has never seen, not just on re-worded copies of the same message.
"""
import csv
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
rnd = random.Random(2026)

BANKS = {"SBI": "sbi.co.in", "HDFC Bank": "hdfcbank.com", "ICICI Bank": "icicibank.com", "Axis Bank": "axisbank.com",
         "Kotak": "kotak.com", "PNB": "pnbindia.in", "Bank of Baroda": "bankofbaroda.in", "Canara Bank": "canarabank.com"}
BANK_KW = {"SBI": "sbi", "HDFC Bank": "hdfc", "ICICI Bank": "icici", "Axis Bank": "axisbank", "Kotak": "kotak",
           "PNB": "pnb", "Bank of Baroda": "bankofbaroda", "Canara Bank": "canara"}
NAMES = ["Rahul", "Priya", "Amit", "Sneha", "Karan", "Divya", "Rohan", "Ananya", "Vikram", "Neha", "Arjun", "Pooja", "Manish", "Kavya"]
COURIERS = ["DTDC", "Blue Dart", "India Post", "Delhivery", "FedEx", "Ecom Express"]
COMPANIES = ["Infosys", "TCS", "Wipro", "Capgemini", "Accenture", "HCL", "Tech Mahindra"]
SCAM_TLDS = ["xyz", "top", "click", "live", "icu", "vip", "buzz", "online", "site", "shop", "cfd", "work"]
SHORT = ["bit.ly", "tinyurl.com", "rb.gy", "cutt.ly", "is.gd", "shorturl.at"]
LEGIT_SITES = ["amazon.in", "flipkart.com", "swiggy.com", "zomato.com", "irctc.co.in", "paytm.com", "phonepe.com", "myvi.in", "jio.com", "airtel.in"]


def rand_phone():
    return str(rnd.choice("6789")) + "".join(str(rnd.randint(0, 9)) for _ in range(9))


def rand_otp():
    return "".join(str(rnd.randint(0, 9)) for _ in range(rnd.choice([4, 6, 6, 6])))


def rand_str(n=6):
    return "".join(rnd.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(n))


def scam_link(bank=None):
    kw = BANK_KW.get(bank, rnd.choice(list(BANK_KW.values())))
    k = rnd.randint(0, 6)
    tld = rnd.choice(SCAM_TLDS)
    if k == 0:
        return "http://%s-kyc-update.%s/login" % (kw, tld)
    if k == 1:
        return "%s.%s/%s" % (rnd.choice(SHORT), "", rand_str()) if False else "%s/%s" % (rnd.choice(SHORT), rand_str(7))
    if k == 2:
        return "https://%s-secure%d.%s" % (kw, rnd.randint(10, 999), tld)
    if k == 3:
        return "https://secure.%s.com.verify-%s.%s/kyc" % (kw, rand_str(4), tld)
    if k == 4:
        return "www.%s-rewards.%s/claim" % (kw, tld)
    if k == 5:
        return "https://%s.weebly.com/" % (kw + "-help")
    return "http://%d.%d.%d.%d/%s" % (rnd.randint(11, 220), rnd.randint(1, 250), rnd.randint(1, 250), rnd.randint(1, 250), rnd.choice(["pay", "verify", "login"]))


SLOTS = {
    "bank": lambda c: rnd.choice(list(BANKS)),
    "name": lambda c: rnd.choice(NAMES),
    "name2": lambda c: rnd.choice(NAMES),
    "amt": lambda c: rnd.choice(["Rs %d" % rnd.choice([250, 450, 799, 1200, 2500, 4999, 9800]), "₹%s" % rnd.choice(["350", "1,250", "6,400", "12,000", "18,500"]), "Rs.%d" % rnd.choice([99, 499, 1499])]),
    "big": lambda c: rnd.choice(["Rs 25,00,000", "₹10 lakh", "Rs 50,00,000", "₹5,00,000", "Rs 1 crore"]),
    "fee": lambda c: rnd.choice(["Rs 99", "₹149", "Rs 499", "₹1,200", "Rs 2,500", "₹5,000"]),
    "phone": lambda c: rand_phone(),
    "otp": lambda c: rand_otp(),
    "date": lambda c: rnd.choice(["12-Nov", "15 Nov", "20/11", "03-Dec", "28 Nov", "1 Dec"]),
    "time": lambda c: rnd.choice(["9:30 pm", "10 pm", "6:45 pm", "11:15 am", "8 pm", "4:30 pm"]),
    "card": lambda c: "XX%d" % rnd.randint(1000, 9999),
    "courier": lambda c: rnd.choice(COURIERS),
    "co": lambda c: rnd.choice(COMPANIES),
    "n": lambda c: str(rnd.randint(2, 12)),
    "hrs": lambda c: rnd.choice(["2", "3", "6", "12", "24"]),
    "pct": lambda c: rnd.choice(["30", "45", "60", "100", "150", "200"]),
    "ref": lambda c: str(rnd.randint(100000, 999999)),
    "scamlink": lambda c: scam_link(c.get("bank")),
    "site": lambda c: rnd.choice(LEGIT_SITES),
    "bankdom": lambda c: BANKS.get(c.get("bank") or "SBI", "sbi.co.in"),
    "tid": lambda c: "".join(str(rnd.randint(0, 9)) for _ in range(10)),
}

SCAM_PREFIX = ["", "", "", "Dear Customer, ", "ALERT: ", "URGENT! ", "Dear {name}, ", "NOTICE: ", "Hi, ", "Final reminder: "]
LEGIT_PREFIX = ["", "", "", "Hi {name}, ", "Hello, ", "Dear Customer, ", "Reminder: "]

# (template_id, text). ~50 scam templates covering the main Indian fraud patterns, English and Hinglish.
SCAM = [
    ("kyc1", "Dear Customer, your {bank} KYC has expired. Update now at {scamlink} or your account will be blocked within {hrs} hours."),
    ("kyc2", "{bank}: Your account is suspended due to incomplete KYC. Click {scamlink} to verify immediately."),
    ("kyc3", "Your PAN card is not linked with your {bank} account. Update today to avoid penalty: {scamlink}"),
    ("kyc4", "Aapka {bank} KYC pending hai. Account band ho jayega. Abhi update karein {scamlink}"),
    ("kyc5", "URGENT: {bank} netbanking will be deactivated today. Complete e-KYC by calling {phone}."),
    ("kyc6", "Your Aadhaar verification is pending. Your {bank} account will be suspended tonight. Verify: {scamlink}"),
    ("otp1", "This is {bank} executive. Please share the OTP sent to your mobile to stop the unauthorised transaction of {amt}."),
    ("otp2", "Your {bank} card is being blocked. Reply with your card number, expiry and the OTP you receive to cancel."),
    ("otp3", "Sir apka OTP {otp} batao, aapke account se {amt} debit ho raha hai, rokne ke liye turant share karein."),
    ("otp4", "Customer care here. To process your refund of {amt}, tell us the 6 digit OTP you just got."),
    ("upi1", "You have a pending collect request of {amt}. To receive the money, enter your UPI PIN."),
    ("upi2", "Refund of {amt} approved. Scan this QR code and enter PIN to receive it in your account."),
    ("upi3", "Congrats {name}! Your cashback of {amt} is ready. Approve the request on PhonePe to receive it now."),
    ("prize1", "Congratulations! You have won {big} in the KBC lucky draw. Pay {fee} processing fee to claim your prize. Call {phone}."),
    ("prize2", "You are the lucky winner of an iPhone 15! Claim your gift here: {scamlink} Offer expires in {hrs} hours."),
    ("prize3", "Dear {name}, your mobile number has been selected for a lottery of {big}. Contact {phone} on WhatsApp to claim."),
    ("prize4", "{bank} reward points worth {amt} will expire today. Redeem now: {scamlink}"),
    ("prize5", "Aapne {big} ka inaam jeeta hai! Claim karne ke liye {fee} bhejein aur {phone} par call karein."),
    ("job1", "Work from home! Earn Rs {pct}0 per day by liking videos. No experience needed. Join our Telegram group: {scamlink}"),
    ("job2", "Part time job offer: earn ₹{pct}00 daily with simple tasks. Pay {fee} registration fee to start. WhatsApp {phone}."),
    ("job3", "Hiring freshers for data entry job from home, salary ₹{pct}00/day. Apply on WhatsApp {phone}."),
    ("job4", "We found your profile. Review products on Amazon and get paid {amt} per task. Contact us on Telegram."),
    ("job5", "Ghar baithe kamao ₹{pct}00 daily! Sirf like aur subscribe karna hai. Telegram join karein {scamlink}"),
    ("courier1", "Your {courier} parcel is held due to incorrect address. Pay {fee} redelivery fee here: {scamlink}"),
    ("courier2", "{courier}: Delivery failed. Update your address and reschedule within {hrs} hours: {scamlink}"),
    ("courier3", "A parcel in your name has been detained by customs. Pay clearance charges of {fee} to release it. Call {phone}."),
    ("courier4", "Your package is stuck at {courier} hub. Confirm your address to avoid return: {scamlink}"),
    ("util1", "Dear consumer, your electricity will be disconnected tonight at {time} as your bill is unpaid. Call officer {phone} immediately."),
    ("util2", "Power supply to your meter will be cut today. Update bill details now by contacting {phone}."),
    ("util3", "Your gas connection will be discontinued. Pay pending amount via {scamlink} to avoid disconnection tonight."),
    ("invest1", "Join our VIP stock tips group on WhatsApp and earn {pct}% guaranteed returns. {scamlink}"),
    ("invest2", "Double your money in {n} days with crypto trading. Assured profit. Invest now: {scamlink}"),
    ("invest3", "Insider trading signals, 90% accuracy. Join Telegram channel, daily profit guaranteed. {phone}"),
    ("invest4", "Invest ₹5000 today and get ₹{pct}00 daily returns, risk free. Limited seats."),
    ("loan1", "Instant pre-approved loan of {big} without documents or CIBIL check. Pay {fee} processing fee. Apply: {scamlink}"),
    ("loan2", "Aapka loan approved in 5 minutes, no documents needed. Processing fee {fee}. Call {phone}."),
    ("auth1", "This is CBI cyber cell. A parcel in your name contains illegal drugs. You are under digital arrest. Do not tell anyone. Call {phone}."),
    ("auth2", "Your Aadhaar has been used in a money laundering case. Police will arrest you today. Contact officer on {phone} immediately."),
    ("auth3", "TRAI notice: your SIM will be disconnected in {hrs} hours for illegal activity. Press 1 to talk to officer."),
    ("tax1", "Income tax refund of {amt} approved for you. Submit your bank details to claim: {scamlink}"),
    ("tax2", "IT department: you have a pending refund of {amt}. Click {scamlink} to receive it in {hrs} hours."),
    ("sim1", "Your SIM will be blocked today. Upgrade to 5G SIM by clicking {scamlink}"),
    ("remote1", "To fix the issue, install AnyDesk and share the 9 digit code with our support executive."),
    ("remote2", "Your {bank} account is at risk. Download the security app from {scamlink}/secure.apk and install it."),
    ("cred1", "Verify your debit card number and ATM PIN to avoid account closure: {scamlink}"),
    ("gift1", "Buy Amazon Pay gift cards worth {fee} and send us the codes to clear your pending tax."),
    ("credit1", "Your {bank} credit card limit has been increased to {big}. Activate here: {scamlink}"),
    ("upi4", "Payment of {amt} is stuck. Share your UPI ID and PIN so we can release it."),
    ("fee1", "Dear {name}, your {bank} loan is approved. Deposit {fee} refundable security amount to {phone} to release funds."),
    ("job6", "Congratulations, you are shortlisted by {co}. Pay {fee} training deposit to confirm your joining. No interview needed."),
    ("prize6", "Amazon lucky draw: you have been selected to win a free smartphone. Pay shipping {fee} here: {scamlink}"),
    ("threat1", "Your electricity and gas connection will be terminated. Contact officer {phone} now, do not ignore this message."),
]

# Genuine messages, including hard cases that share words with scams (OTP, links, urgent, won, KYC, blocked).
LEGIT = [
    ("otp_l1", "{otp} is your OTP for {bank} login. Do not share it with anyone. -{bank}"),
    ("otp_l2", "Your one time password for transaction of {amt} is {otp}. Never share this OTP. {bank} will never call to ask for it."),
    ("otp_l3", "{otp} is your Swiggy verification code. It is valid for 10 minutes."),
    ("otp_l4", "Use {otp} as the login code for your Paytm account. Do not share it."),
    ("txn1", "{amt} debited from a/c {card} on {date} via UPI Ref {ref}. Avl bal Rs 12,430. -{bank}"),
    ("txn2", "{amt} credited to your a/c {card} on {date}. Ref {ref}. -{bank}"),
    ("txn3", "Your salary of {amt} has been credited to account {card} on {date}."),
    ("txn4", "Thank you for paying {amt} to {name} on UPI. Ref no {ref}."),
    ("bill1", "Your electricity bill of {amt} is due on {date}. Pay from the official app or {site}/bill. Ignore if already paid."),
    ("bill2", "Your credit card statement of {amt} is generated. Minimum due by {date}. Pay in the {bank} mobile app."),
    ("bill3", "EMI of {amt} for your {bank} loan will be auto-debited on {date}. Keep sufficient balance in your account."),
    ("deliv1", "Your Amazon order has been shipped and will arrive by {date}. Track here: amazon.in/orders"),
    ("deliv2", "{courier}: Your package is out for delivery today. Delivery partner {name} will call you. Track: {courier}.com"),
    ("deliv3", "Your Swiggy order is being prepared and will reach you in {n}0 minutes."),
    ("deliv4", "Order delivered. Rate your experience of the {site} order in the app."),
    ("cab1", "Your Uber ride is arriving in {n} minutes. OTP for the trip is {otp}. Share only with your driver {name}."),
    ("train1", "PNR {tid}: Your IRCTC ticket is confirmed for {date}. Train 12951, departs 4:30 pm. Have a safe journey."),
    ("flight1", "Web check-in is now open for your flight on {date}. Check in at the airline's official app. Gate closes 45 minutes before departure."),
    ("appt1", "Reminder: Your appointment with Dr. {name} is on {date} at {time}. Please reach 10 minutes early."),
    ("appt2", "Your dentist visit is confirmed for {date}, {time}. Reply 1 to confirm or 2 to reschedule."),
    ("hr1", "Hi {name}, this is HR from {co}. Your interview is scheduled on {date} at {time}. Meeting link: meet.google.com/abc-defg-hij"),
    ("hr2", "Congratulations {name}, you have cleared the technical round at {co}. HR will email the next steps from your official company id."),
    ("hr3", "Hi {name}, please share your updated resume on the careers portal at least a day before the interview on {date}."),
    ("work1", "Team standup moved to {time} today. Same Zoom link as always."),
    ("work2", "Can you send the report by {time}? The client meeting is on {date}."),
    ("work3", "Hi {name}, deck is ready. I have shared it on Google Drive. Please review before tomorrow's call."),
    ("friend1", "Bhai kal movie chalte hain? Show {time} ka hai, I'll book the tickets."),
    ("friend2", "Happy birthday {name}! Have an amazing year ahead. Party on {date}, don't be late."),
    ("friend3", "We won the match by {n} wickets! Congrats team, treat is on me."),
    ("friend4", "Mom is asking when you are coming home. Dinner at {time}, she made your favourite."),
    ("friend5", "Yaar please send me the notes for the lecture. Exam is on {date} and I missed two classes."),
    ("friend6", "Did you reach? Call me when you get home. I'll be up till {time}."),
    ("friend7", "Rent of {amt} sent to you on GPay, please check and confirm. Thanks {name}!"),
    ("promo1", "Big Billion sale starts {date}. Up to {pct}% off on electronics. Shop on {site}. T&C apply."),
    ("promo2", "Your Netflix subscription renews on {date}. Manage your plan in the app. No action needed."),
    ("promo3", "Hi {name}, your Zomato Gold membership is expiring on {date}. Renew in the app to keep your benefits."),
    ("promo4", "Flash sale ends tonight at midnight! Extra 10% off for app users on {site}. Open the app to shop."),
    ("kyc_l1", "Your KYC verification is complete. Thank you for updating your details with {bank}. No further action needed."),
    ("kyc_l2", "Dear customer, as per RBI guidelines please visit your nearest {bank} branch with ID proof to update KYC before {date}."),
    ("aware1", "{bank} warns: never share your OTP, PIN or password with anyone. We will never ask for it. Report fraud on 1930."),
    ("aware2", "Beware of fake calls. Do not install apps like AnyDesk at anyone's request, and never share your card details."),
    ("block_l1", "As requested, your {bank} debit card ending {card} has been blocked. Order a new card in the app."),
    ("edu1", "Exam results for semester {n} are published on the college portal. Login with your roll number to view marks."),
    ("edu2", "Reminder: fee submission last date is {date}. Pay on the official college website or visit the accounts office."),
    ("edu3", "Class assignment due on {date}. Submit on the LMS before {time}. Late submissions will lose marks."),
    ("tel1", "Your {site} recharge of {amt} was successful. Validity extended till {date}. Thank you."),
    ("tel2", "Your Jio plan expires on {date}. Recharge from the MyJio app to continue enjoying benefits."),
    ("govt1", "Your Aadhaar update request has been received. Check status on uidai.gov.in using your URN. Never share OTP."),
    ("govt2", "Income tax return for AY 2025-26 processed. Refund, if any, will be credited to your pre-validated bank account. Check status at incometax.gov.in"),
    ("pay1", "{name} requested {amt} on UPI for dinner. Open your payment app to review and pay if you know this person."),
    ("pay2", "Your payment of {fee} to {site} was successful. Order id {ref}."),
    ("order1", "Your order from {site} cannot be delivered today. A new delivery date has been set. Check the app for details."),
    ("sec1", "New login to your account from Chrome on Windows. If this was not you, change your password in the app."),
    ("fam1", "Papa's reports are normal. Doctor said to continue the same medicines. Will call you tonight."),
    ("hindi1", "Aaj office se late aaunga, khana kha lena. Kal subah {time} ki train hai."),
    ("hindi2", "Namaste, aapka {bank} account statement is mahine ka ready hai. App mein dekh sakte hain."),
]


def fill(template, label):
    ctx = {}

    def repl(m):
        key = m.group(1)
        if key not in ctx:
            ctx[key] = SLOTS[key](ctx)
        return ctx[key]

    prefix = rnd.choice(SCAM_PREFIX if label == 1 else LEGIT_PREFIX)
    if re.match(r"(?i)(hi|hello|dear|alert|urgent|notice|reminder|final)\b", template):
        prefix = ""
    txt = re.sub(r"\{(\w+)\}", repl, prefix + template)
    return txt


def build(variants=12):
    rows = []
    for label, items in ((1, SCAM), (0, LEGIT)):
        for tid, tpl in items:
            seen = set()
            tries = 0
            while len(seen) < variants and tries < variants * 6:
                tries += 1
                t = fill(tpl, label)
                if t not in seen:
                    seen.add(t)
                    rows.append({"text": t, "label": label, "template": tid})
    rnd.shuffle(rows)
    return rows


if __name__ == "__main__":
    rows = build()
    path = os.path.join(HERE, "seed_train.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "label", "template"])
        w.writeheader()
        w.writerows(rows)
    n1 = sum(r["label"] for r in rows)
    print("wrote %d rows (%d scam, %d legit) from %d templates -> %s" % (len(rows), n1, len(rows) - n1, len(SCAM) + len(LEGIT), path))
