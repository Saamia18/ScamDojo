"""Blind test set: written AFTER the engine rules and thresholds were frozen. Never used for tuning.

It deliberately includes hard cases (scams with no obvious keywords, genuine messages full of scary words).
Failures here are reported on the Under-the-hood page instead of being fixed behind the scenes.
"""
import csv, os
HERE = os.path.dirname(os.path.abspath(__file__))

SCAM = [
 ("kyc", "Respected customer, your Union Bank account shall be deactivated after 24 hrs due to pending KYC. Kindly update at unionbank-kyc-help.cfd"),
 ("kyc", "Canara Bank alert: Your net banking access has been suspended. Reactivate now by verifying PAN at canara-reactivate.top/login"),
 ("otp", "Hello sir, I am from Amazon support. Your order is being refunded, please share the OTP you just received to complete it."),
 ("otp", "Don't worry, this is only for verification. Tell me the 4 digit code that came on your phone so I can unblock your card."),
 ("upi", "Rs 4,500 has been sent to you. Please accept the payment request in your UPI app by entering your PIN to receive the money."),
 ("prize", "Dear Sir/Madam, you are the 1000th visitor of our site and have won a Royal Enfield! Send Rs 2,100 as delivery fee to claim."),
 ("prize", "Tata Capital lucky draw result: your name is selected for Rs 12 lakh cash prize. Call 7001234567 to claim."),
 ("job", "Earn money while sitting at home! Just complete small online tasks, Rs 800 per task, withdraw anytime. Chat with HR on WhatsApp +91 90000 12345"),
 ("job", "Urgent hiring: Flipkart delivery partners, joining fee Rs 1,500 refundable after first week. Apply now: flipkart-careers-hiring.top"),
 ("courier", "FedEx: Your parcel from abroad is waiting. Customs duty of Rs 849 is unpaid. Pay at fedex-duty-pay.click within 12 hours or it is returned."),
 ("courier", "Your Amazon delivery attempt failed. Confirm address and pay Rs 20 at amzn-redelivery.cfd/track"),
 ("util", "Your electricity bill has not been updated and supply will be cut tonight by 8:30 pm. Contact the electricity officer on 8800123456 for immediate update."),
 ("invest", "Join our stock market learning group. Members make 5 to 10 percent profit every single day with our expert calls. Guaranteed. t.me/stockwin_india"),
 ("invest", "Bitcoin giveaway! Send 0.01 BTC and receive double back instantly. Limited time only."),
 ("loan", "Congratulations! Your instant personal loan of Rs 3,00,000 is approved. Pay Rs 1,800 insurance charges to disburse. Call 9876012345."),
 ("authority", "Customs department: a parcel containing prohibited items has been booked in your name. To avoid arrest, contact inspector on 8123456789 immediately."),
 ("authority", "Notice from Supreme Court of India: FIR registered under your Aadhaar. Appear online today and do not tell anyone, call the number on this message."),
 ("refund", "Dear taxpayer, your refund of Rs 24,780 is pending due to wrong account number. Click here to correct your bank details: incometaxindia-refund.xyz"),
 ("remote", "We need to verify your identity. Please install TeamViewer and send us your ID and password."),
 ("apk", "Your electricity KYC is incomplete. Install the Vidyut Mitra app from this link to avoid disconnection: vidyut-kyc.top/app.apk"),
 ("cred", "For your safety please reply with your debit card number, expiry date and CVV to keep your account active."),
 ("family", "Hello beta, this is Uncle. My phone is broken so I am using a friend's number. Please send 25000 on GPay right now, it is urgent, will return tomorrow."),
 ("family", "Hi Dad, I changed my number, this is my new one. Can you transfer some money urgently for my fees? Can't talk now."),
 ("phish", "Your SBI YONO account is locked due to suspicious activity. Unlock it here: https://sbi-yono-unlock.shop"),
 ("phish", "Microsoft Security: Your PC is infected. Call our toll free support on 9988001122 right now to remove the virus."),
 ("hinglish", "Aapka PAN card band hone wala hai, abhi link click karke update karein warna fine lagega: pan-update-india.top"),
 ("hinglish", "Mubarak ho! Aapne Rs 25 lakh jeete hain. Paise lene ke liye pehle Rs 3000 processing fee bhejein."),
 ("obf", "Y O U R  H D F C  A C C O U N T  I S  B L O C K E D, click hdfc-unblock.cfd now"),
 ("subtle", "Hi, I found your number from a job site. I have a simple part time role, 20 minutes a day, daily payments. Interested? Reply YES and I'll send details on Telegram."),
 ("subtle", "Hey, is this still your number? I have your parcel but the address is unclear, please open the tracking link: trk-parcel.live/8841"),
]

LEGIT = [
 ("bank", "INR 1,200.00 spent on HDFC Bank Card x9921 at AMAZON PAY on 09-Nov-26. Available limit INR 84,300. Not you? Call 18002586161."),
 ("bank", "Your ICICI Bank account XX3321 has been credited with Rs 7,500 by NEFT from RAJESH KUMAR on 08-Nov."),
 ("bank", "Alert: Rs 15,000 withdrawn from ATM on 10 Nov at 14:12. If not done by you, block your card in the app and call customer care."),
 ("bank", "Dear Customer, kindly visit your home branch with ID proof to update your KYC. The last date is 31 Dec. No online link is required."),
 ("bank", "SBI: Never click on links in SMS asking you to update KYC or account details. SBI never asks for OTP. Report fraud at cybercrime.gov.in."),
 ("otp", "Your OTP to log in to Zerodha Kite is 774120. Valid for 5 minutes. Do not share with anyone."),
 ("otp", "123987 is the OTP for your IRCTC login. Please do not disclose it to anybody."),
 ("delivery", "Your Myntra order will be delivered tomorrow by 8 pm. Track it in the app under Orders."),
 ("delivery", "BlueDart: shipment AWB 20398421 is out for delivery. Our executive will contact you shortly."),
 ("travel", "Your flight AI 804 on 14 Nov is on time. Boarding starts at 06:10 from gate 22. Carry a valid photo ID."),
 ("travel", "Your Rapido ride has been booked. Captain Ramesh will arrive in 3 minutes. Share OTP 5521 to start the trip."),
 ("work", "Urgent: client call moved to 11 am today. Please join on Teams, link in the calendar invite."),
 ("work", "Hi Neha, the offer letter has been uploaded to the HR portal. Please sign and return by Friday. Welcome to the team!"),
 ("work", "Your account password will expire in 7 days. Please reset it from the IT self-service portal on the intranet."),
 ("friend", "Congrats yaar!! You won the hackathon, treat tonight at my place?"),
 ("friend", "Can you please send me the link to the Zoom class? I forgot to save it."),
 ("friend", "I will pay you the Rs 800 for the tickets tonight, I'll send it on PhonePe after dinner."),
 ("friend", "Hey, my phone is dead so using my brother's number. Reach by 8, save this number for now."),
 ("friend", "Arre bhai blocked ho gaya kya tera number? Call nahi lag raha, WhatsApp pe reply kar."),
 ("friend", "Machaan, college WhatsApp group mein notice aaya hai, kal ki exam postpone ho gayi."),
 ("promo", "Hurry! Last 2 hours to grab up to 60% off on Nykaa Pink Friday Sale. Shop now on the Nykaa app."),
 ("promo", "Your Amazon Prime membership renews on 22 Nov. You can cancel anytime from Your Account on amazon.in."),
 ("promo", "Reminder: your LIC premium of Rs 4,200 is due on 25 Nov. Pay through the LIC Pay app or the official website licindia.in."),
 ("govt", "Your PAN application has been received. Acknowledgement number 7845123. Check status on the NSDL website."),
 ("govt", "Your vehicle challan of Rs 500 has been generated. View and pay it on the official parivahan.gov.in portal."),
 ("edu", "Congratulations! You have been shortlisted for the campus placement at Deloitte. Interview schedule has been posted on the placement portal."),
 ("health", "Your COVID booster appointment is confirmed at Fortis Hospital on 15 Nov at 10 am. Carry your Aadhaar card."),
 ("family", "Beta, I have transferred Rs 5,000 to your account for the books, tell me once it reaches."),
 ("pay", "You received Rs 1,000 from Anita Sharma on UPI. Ref 4412398210. Total balance is now visible in your app."),
 ("misc", "Your Airbnb stay in Goa is confirmed for 20 Nov. Check-in details and host contact are available in the app."),
]

if __name__ == "__main__":
    path = os.path.join(HERE, "india_blindset.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["text", "label", "kind"])
        for k, t in SCAM:
            w.writerow([t, 1, k])
        for k, t in LEGIT:
            w.writerow([t, 0, k])
    print("blindset: %d scam, %d legit -> %s" % (len(SCAM), len(LEGIT), path))
