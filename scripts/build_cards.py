"""Writes web/data/cards.json (for the game) and engine/data/cards_eval.csv (so the engine is scored on the game cards)."""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from card_i18n import CARDS as TR, BOSSES as BTR
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOSSES = [
    dict(id="kraken", name="KYC Kraken", emoji="🦑", color="#6A4CFF", category="kyc", hp=70,
         tagline="Grabs accounts with fake KYC deadlines.",
         intro="Your account will be BLOCKED! Update KYC right now!",
         defeat="The Kraken drops your account details and sinks back into the sea.",
         lesson="Banks never ask you to complete KYC through a link or a call from a random number."),
    dict(id="llama", name="Lottery Llama", emoji="🦙", color="#D6247F", category="prize", hp=70,
         tagline="Says you won prizes you never entered.",
         intro="You are the lucky winner! Just pay a tiny fee...",
         defeat="The Llama spits out your prize money and trots off.",
         lesson="You cannot win a draw you never entered, and real prizes never ask for a fee."),
    dict(id="octopus", name="OTP Octopus", emoji="🐙", color="#E2362F", category="otp", hp=70,
         tagline="Eight arms, all reaching for your OTP and PIN.",
         intro="Just read me the code on your phone, it is only for verification.",
         defeat="The Octopus retreats into the ink with empty arms.",
         lesson="Never share an OTP or UPI PIN. Receiving money never needs your PIN."),
    dict(id="jackal", name="Job Offer Jackal", emoji="🐺", color="#1E9E5A", category="job", hp=70,
         tagline="Promises easy money for liking videos.",
         intro="Earn Rs 5,000 a day from your couch. Registration fee only Rs 999!",
         defeat="The Jackal drops the fake offer letters and flees.",
         lesson="Real employers never charge you to hire you and never pay for likes or ratings."),
    dict(id="cobra", name="Courier Cobra", emoji="🐍", color="#FFB400", category="courier", hp=70,
         tagline="Hisses about stuck parcels and power cuts.",
         intro="Your parcel is stuck at customs. Pay now or it is returned!",
         defeat="The Cobra slithers away, parcel-less.",
         lesson="Track parcels only in the shop's app. Utilities don't cut power by SMS at night."),
]

# (sender, text, is_scam, loss, lesson)
CARDS = {
 "kraken": [
  ("VK-SBIINB", "Dear SBI user, your YONO account is restricted. Complete KYC today: http://yono-sbi-care.top/kyc or lose access.", 1, 3000, "SBI's real site is sbi.co.in. This link is a look-alike, and banks don't restrict accounts by SMS link."),
  ("AD-HDFCBK", "HDFC Bank: PAN not updated. Netbanking will be blocked in 3 hours. Update: hdfc-pan-link.xyz", 1, 2500, "A 3-hour deadline plus a strange .xyz link is a classic panic trick."),
  ("+91 99012 33410", "Sir this is ICICI KYC department. Your KYC will expire tonight, call me on this number to renew now.", 1, 2000, "Banks don't renew KYC through a call from a random number."),
  ("BZ-AXISBK", "Axis Bank: Your account will be frozen in 24 hrs due to Aadhaar mismatch. Verify at axis-aadhaar-verify.cfd/login", 1, 3500, "Look at the ending: .cfd is not a bank. Real Axis Bank is axisbank.com."),
  ("VM-PNBSMS", "PNB customer, KYC pending. Pay Rs 10 verification fee at pnb-secure-kyc.click to keep your account active.", 1, 1500, "A 'small fee' is how they capture your card details."),
  ("+91 88002 45671", "Hello, your SIM KYC is expiring. Send your Aadhaar photo and OTP to this number to continue service.", 1, 3000, "Never send Aadhaar photos or OTPs to a number that texts you."),
  ("TX-KOTAKB", "Kotak: To avoid account suspension, update your PAN here: bit.ly/3kt0kyc", 1, 2000, "A shortened link hides where you'll land."),
  ("VK-SBIINB", "Your SBI account KYC is up to date. No action is required. Thank you for banking with us.", 0, 0, "Genuine: it asks you to do nothing, has no link and makes no threat."),
  ("AD-HDFCBK", "HDFC Bank: Your periodic KYC update is due by 31 Dec. Please visit your branch with ID proof. No link is being sent.", 0, 0, "Genuine: it sends you to a branch and explicitly sends no link."),
  ("BK-ICICIB", "ICICI Bank: Rs 3,200 debited from A/c XX5521 at Reliance Digital on 10-Nov. Not you? Call 1800 1080 immediately.", 0, 0, "Genuine: a normal debit alert with the number printed on your card."),
  ("Mom", "Beta, bank wale ne call kiya tha KYC ke liye. Maine bola main branch aake karunga. Theek hai na?", 0, 0, "Genuine chat, and a good instinct: verifying in person is the right move."),
 ],
 "llama": [
  ("+91 73310 88224", "CONGRATULATIONS! Your number won Rs 15,00,000 in the Jio Diwali Bumper. Send Rs 2,500 tax to claim. Call 7331088224.", 1, 2500, "A prize that needs you to pay tax first is a scam. Real winners are never asked to pay."),
  ("VM-AMZNIN", "Amazon Mega Draw: you're the winner of an iPhone 16. Claim before midnight: amazon-megadraw.shop/win", 1, 3000, "amazon.in is the real site. .shop with 'megadraw' is a trap."),
  ("JK-PAYTMB", "Paytm Wheel: spin and win up to Rs 10,000 cashback! Tap https://paytm-spin.live/win", 1, 2000, "Paytm only runs offers inside its own app."),
  ("+91 95500 12987", "Dear lucky customer, you are selected for a free Royal Enfield. Pay Rs 3,999 registration to book it.", 1, 3999, "Free vehicle plus registration fee: the fee is the whole scam."),
  ("BH-FLPKRT", "Flipkart Anniversary: Your gift voucher worth Rs 5,000 expires in 2 hrs. Redeem at flipkart-gifts.click", 1, 2500, "A 2-hour expiry and a .click link push you to act before you think."),
  ("+91 70110 44556", "Hello, KBC lucky draw 2026. You won 25 lakh. Do not share this with anyone. Contact Mr Rana on WhatsApp.", 1, 3500, "'Don't tell anyone' is how scammers stop others from warning you."),
  ("AX-HDFCRW", "HDFC reward points Rs 8,950 will lapse today. Redeem via hdfc-rewards-now.top", 1, 2000, "The real bank site is hdfcbank.com, never a '-rewards-now.top' address."),
  ("VM-AMZNIN", "Amazon: Prime Day deals start tomorrow at 12 noon. Open the Amazon app to see them. No code needed.", 0, 0, "Genuine: it points you to the app and wants nothing from you."),
  ("Rohan", "Bro we won the quiz!! Prize is a Rs 500 voucher, will share it with the team.", 0, 0, "Genuine: a friend who actually took part in the quiz."),
  ("AX-ZOMATO", "Zomato: Rs 100 off your next order, auto-applied at checkout. Valid till Sunday.", 0, 0, "Genuine: a discount applied automatically, with no link or fee."),
  ("Fest Team", "Congratulations! Your fest raffle ticket #214 won the second prize. Collect your hamper from the student desk with your ID.", 0, 0, "Genuine: you did buy a ticket, and you collect it in person with no payment."),
 ],
 "octopus": [
  ("+91 98200 11223", "Sir I'm from SBI fraud team. A payment of Rs 49,999 is pending. Share the OTP now to stop it.", 1, 3500, "Fraud teams don't need your OTP. The code is what lets the thief in."),
  ("+91 90040 66778", "Wrong transfer: I sent you Rs 5,000 by mistake. Please accept my request and enter PIN to send it back.", 1, 3000, "Entering a PIN sends money OUT. You never need a PIN to receive."),
  ("VM-GPAYIN", "GPay: Your Rs 2,000 reward is ready. Open the request in your app and enter UPI PIN to receive.", 1, 2000, "'Receive' plus 'enter PIN' can't both be true."),
  ("+91 81230 99010", "Your electricity subsidy of Rs 1,500 is approved. Scan the QR attached and put your PIN to get it.", 1, 1500, "Scanning a QR and entering a PIN pays money away. It never brings money in."),
  ("+91 99870 55123", "I'm calling from Airtel. Your SIM will deactivate, read me the code that just came to you.", 1, 2500, "That code is an OTP. Never read it to anyone who called you."),
  ("BK-ICICIB", "ICICI: Card blocked. Reply with the OTP sent to you and your card CVV to unblock.", 1, 3000, "Banks never ask for the CVV or OTP by message."),
  ("+91 70001 22334", "Refund on your order is stuck. Share your UPI PIN so the refund can be released.", 1, 2000, "No refund ever needs your PIN."),
  ("VK-HDFCBK", "845120 is your OTP for HDFC NetBanking login. Valid 5 mins. Do not share with anyone, HDFC never asks.", 0, 0, "Genuine: you asked for this code, and it warns you not to share it."),
  ("JD-PHONEP", "PhonePe: You paid Rs 120 to Sharma Tea Stall. UPI Ref 4455667788. Check history in the app.", 0, 0, "Genuine: a plain receipt for a payment you made."),
  ("Amit", "Sent you Rs 1,000 for the movie tickets. Check GPay and let me know!", 0, 0, "Genuine: a friend telling you to check your own app, with no request to approve."),
  ("AX-UBERIN", "Your Uber OTP is 3351. Share it with the driver only when you board.", 0, 0, "Genuine: you booked the ride, and this OTP is meant for the driver."),
 ],
 "jackal": [
  ("+91 70220 31145", "Earn Rs 3,500 daily from home! Just rate hotels on Google. Join WhatsApp group now.", 1, 2500, "Paying for ratings is the classic task scam. It starts free and then asks for deposits."),
  ("+91 99100 77788", "Hi, I'm HR from Amazon. Part-time task job, 30 min/day, Rs 15,000 per week. Telegram me for details.", 1, 3000, "Real HR doesn't recruit from random numbers or move you to Telegram."),
  ("VM-JOBALR", "Selected! Data entry work from home, 40,000/month. Registration fee Rs 999 refundable. Pay: jobs-register.top", 1, 999, "'Refundable' fees are never refunded."),
  ("+91 80100 44332", "Wipro HR: Your joining letter is ready. Pay Rs 6,500 for laptop security deposit to confirm.", 1, 3500, "Companies give you a laptop. They don't ask for deposits."),
  ("+91 63021 55987", "YouTube like task: earn Rs 50 per like. First task free. Click t.me/likestoearn_india", 1, 2000, "The first task pays to hook you, then they ask you to 'invest'."),
  ("+91 98765 11000", "We saw your resume. Easy online job, no interview. Send Rs 1,200 processing fee to start tomorrow.", 1, 1200, "No interview and an upfront fee means there's no job."),
  ("+91 70770 12345", "Congratulations, you got work-from-home with Meesho, Rs 800 per order check. Share Aadhaar and OTP to register.", 1, 3000, "Aadhaar and OTP are for banks and government, not for a job."),
  ("LinkedIn", "A recruiter at TCS viewed your profile. See who is hiring for Business Analyst roles in Mumbai.", 0, 0, "Genuine: a standard platform notification with nothing to pay or share."),
  ("Ritu (HR)", "Hi Sneha, this is Ritu from Infosys HR. Your interview is on Tuesday at 11 am. We'll send a Teams link to your registered email.", 0, 0, "Genuine: scheduled interview, official email, no fee."),
  ("HR Desk", "Your background verification is complete. No payment is required from you at any stage. Welcome aboard!", 0, 0, "Genuine: it explicitly says nothing is payable."),
  ("Placement Cell", "Reminder: Godrej pre-placement talk tomorrow at 5 pm in the Auditorium. Attendance is mandatory.", 0, 0, "Genuine: an in-person college notice."),
 ],
 "cobra": [
  ("VM-DTDCIN", "DTDC: Parcel on hold, address incomplete. Update within 12 hrs: dtdc-address-fix.top/u", 1, 2000, "DTDC's real site is dtdc.in. This one just borrows the name."),
  ("+91 77009 88221", "Your package at Mumbai airport customs needs Rs 2,950 clearance. Pay on 7700988221 UPI to receive.", 1, 2950, "Customs never takes payment on a personal UPI number."),
  ("AD-INDPST", "India Post: delivery failed twice. Reschedule at indiapost-reship.xyz or parcel will be returned.", 1, 1500, "The real site ends in .gov.in. A .xyz address is not India Post."),
  ("+91 99888 12012", "Electricity Dept: your connection will be disconnected at 9:30 pm tonight. Call Mr Patil immediately.", 1, 3000, "Utilities don't disconnect by SMS at night. 'Call Mr Patil' is the hook."),
  ("VK-BLUEDT", "BlueDart: Pay Rs 25 redelivery charge here: bit.ly/bdrs25 to receive your shipment.", 1, 1000, "Tiny fee, hidden link: it's after your card details."),
  ("+91 90909 12345", "This is FedEx. Your parcel to Taiwan contains illegal items. Police case registered. Press 1 to speak to officer.", 1, 3500, "'Drug parcel' calls are a known fear scam. Hang up and call 1930."),
  ("TM-GASAGN", "Gas supply will be stopped due to unpaid bill. Update details now: gas-bill-update.click", 1, 2000, "Check your gas bill in the official app, never via a link like this."),
  ("VM-DLVRY", "Delhivery: Your Myntra order is out for delivery today between 2 and 6 pm. The agent will call you.", 0, 0, "Genuine: no link, no payment, just a delivery window."),
  ("AM-AMZNIN", "Amazon: Your package was delivered to the front door. Rate your delivery experience in the app.", 0, 0, "Genuine: it sends you to the app and asks for nothing else."),
  ("BS-BESCOM", "BESCOM: Your bill of Rs 1,420 for Oct is due on 25 Nov. Pay in the BESCOM app or at the counter.", 0, 0, "Genuine: a due date and the official app, with no threat."),
  ("Dad", "Courier boy called, I told him to leave it with the security. Will you check at 6?", 0, 0, "Genuine: normal family chat about a parcel."),
 ],
}


def main():
    cards = []
    for b in BOSSES:
        b["i18n"] = {lang: dict(zip(("tagline", "intro", "defeat", "lesson"), BTR[b["id"]][lang])) for lang in ("hi", "kn")}
        assert len(TR[b["id"]]["hi"]) == len(CARDS[b["id"]]) == len(TR[b["id"]]["kn"]), b["id"]
        for i, (sender, text, scam, loss, lesson) in enumerate(CARDS[b["id"]], 1):
            channel = "sms" if (sender[:2].isalpha() and "-" in sender) else "chat"
            card = {"id": "%s-%02d" % (b["id"], i), "boss": b["id"], "sender": sender, "channel": channel, "text": text,
                    "scam": bool(scam), "loss": loss, "lesson": lesson, "i18n": {}}
            for lang in ("hi", "kn"):
                ttext, tlesson, flags = TR[b["id"]][lang][i - 1]
                good = [f for f in flags if f in ttext]
                if len(good) != len(flags):
                    print("WARNING: flag not found in %s %s: %s" % (card["id"], lang, [f for f in flags if f not in ttext]))
                if scam and not good:
                    print("WARNING: scam card %s has no flags in %s" % (card["id"], lang))
                card["i18n"][lang] = {"text": ttext, "lesson": tlesson, "flags": good}
            cards.append(card)
    out = os.path.join(ROOT, "web", "data")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "cards.json"), "w", encoding="utf-8") as f:
        json.dump({"bosses": BOSSES, "cards": cards}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "engine", "data", "cards_eval.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "label", "kind"])
        for c in cards:
            w.writerow([c["text"], int(c["scam"]), c["boss"]])
    print("%d cards (%d scam, %d legit) across %d bosses" % (len(cards), sum(c["scam"] for c in cards), sum(not c["scam"] for c in cards), len(BOSSES)))


if __name__ == "__main__":
    main()
