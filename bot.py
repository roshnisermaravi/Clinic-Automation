# ─────────────────────────────────────
# BOT.PY — WhatsApp Conversation Logic
# ─────────────────────────────────────

# ── Add to imports at top of bot.py ──
from sms import (
    build_sms_reply_handler,
    send_appointment_confirmation_sms,
    send_rejection_sms,
)
from appointments import cancel_appointment   # already imported, just confirming
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from appointments import (
    SLOT_LABELS,
    approve_appointment,
    cancel_appointment,
    clean,
    format_available_slot_menu,
    format_available_times,
    get_remaining_times_for_slot,
    get_slot_from_patient_choice,
    is_day_full,
    normalize_whatsapp_number,
    parse_approve_command,
    reject_appointment,
)
from security import (
    is_doctor_number,
    is_doctor_verified,
    validate_twilio_request,
    verify_doctor_pin,
)
from sheets import save_appointment, save_lead
from state import (
    clear_pending_booking,
    clear_state,
    get_pending_booking,
    get_state,
    set_pending_booking,
    set_state,
)

# ─────────────────────────────────────
# STARTUP
# ─────────────────────────────────────
load_dotenv()

TWILIO_ACCOUNT_SID  = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUM = os.getenv("TWILIO_WHATSAPP_NUM", "whatsapp:+14155238886")
DOCTOR_WHATSAPP     = os.getenv("DOCTOR_WHATSAPP")


def _require_env(name, value):
    if not value:
        raise RuntimeError(f"Missing {name}. Add it to your .env file.")
    return value


TWILIO_ACCOUNT_SID = _require_env("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID)
TWILIO_AUTH_TOKEN  = _require_env("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN)
DOCTOR_WHATSAPP    = _require_env("DOCTOR_WHATSAPP", DOCTOR_WHATSAPP)

app = Flask(__name__)
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# ─────────────────────────────────────
# FAQ CONTENT
# ─────────────────────────────────────
MAIN_MENU = (
    "Reply with a number:\n\n"
    "1️⃣ Book Appointment\n"
    "2️⃣ Consultation Fees\n"
    "3️⃣ Doctor & Timings\n"
    "4️⃣ Location & Directions\n"
    "5️⃣ Cancel Appointment\n"
    "6️⃣ Talk to Staff"
)

FAQ_SCRIPT = {
    "hi":        f"👋 Hello! Welcome to *Sunshine Clinic*.\n\nHow can we help you today?\n\n{MAIN_MENU}",
    "hello":     f"👋 Hello! Welcome to *Sunshine Clinic*.\n\nHow can we help you today?\n\n{MAIN_MENU}",
    "hey":       f"👋 Hi there! Welcome to *Sunshine Clinic*.\n\n{MAIN_MENU}",
    "2":         "💰 *Consultation Fees*\n\n• General Consultation — ₹500\n• Follow Up Visit — ₹300\n• Child Consultation — ₹400\n\nPayment accepted: Cash / UPI / Card 💳",
    "3":         "👨‍⚕️ *Our Doctors & Timings*\n\n🩺 Dr. Ramesh Kumar (General Physician)\n🕘 Mon–Sat: 9am–1pm & 5pm–8pm\n\n🩺 Dr. Priya Sharma (Paediatrician)\n🕘 Mon–Fri: 10am–2pm\n\n🚫 Sunday: Closed",
    "4":         "📍 *Location & Directions*\n\n📌 Sunshine Clinic\n42, Anna Salai, Chennai — 600002\n\n🗺 Landmark: Next to State Bank ATM\n\n📞 Call us: +91 98765 43210\n\nGoogle Maps: maps.google.com",
    "6":         "👩‍💼 Connecting you to our staff...\n\nSomeone will reply shortly.\nIf urgent, call us: +91 98765 43210 📞",
    "fee":       "💰 Consultation fee is ₹500 for general and ₹300 for follow up. Reply *2* for full details.",
    "fees":      "💰 Consultation fee is ₹500 for general and ₹300 for follow up. Reply *2* for full details.",
    "cost":      "💰 Consultation fee is ₹500 for general and ₹300 for follow up. Reply *2* for full details.",
    "price":     "💰 Consultation fee is ₹500 for general and ₹300 for follow up. Reply *2* for full details.",
    "timing":    "🕘 We are open Mon–Sat, 9am–8pm. Reply *3* for doctor wise timings.",
    "timings":   "🕘 We are open Mon–Sat, 9am–8pm. Reply *3* for doctor wise timings.",
    "hours":     "🕘 We are open Mon–Sat, 9am–8pm. Reply *3* for doctor wise timings.",
    "open":      "🕘 Yes! We are open Mon–Sat, 9am–8pm. Sunday closed.",
    "doctor":    "👨‍⚕️ We have Dr. Ramesh Kumar and Dr. Priya Sharma. Reply *3* for their timings.",
    "location":  "📍 We are at 42, Anna Salai, Chennai. Reply *4* for full directions.",
    "address":   "📍 We are at 42, Anna Salai, Chennai. Reply *4* for full directions.",
    "emergency": "🚨 For emergencies please call us immediately: +91 98765 43210 📞",
    "urgent":    "🚨 For urgent cases please call: +91 98765 43210 📞",
    "thanks":    "🙏 You are welcome! Wishing you good health. 😊",
    "thank":     "🙏 You are welcome! Wishing you good health. 😊",
    "bye":       "👋 Goodbye! Take care and stay healthy. 🌟",
}

DEFAULT_REPLY = "🤖 Sorry, I didn't understand that.\n\n" + MAIN_MENU


# ─────────────────────────────────────
# HELPERS
# ─────────────────────────────────────
def send_whatsapp(to: str, message: str):
    try:
        twilio_client.messages.create(from_=TWILIO_WHATSAPP_NUM, to=to, body=message)
        print(f"✅ WhatsApp sent to {to}")
    except Exception as e:
        print(f"⚠️ WhatsApp send error: {e}")


def get_faq_reply(message: str) -> str:
    msg = message.strip().lower()
    for keyword, reply in FAQ_SCRIPT.items():
        if keyword in msg:
            return reply
    return DEFAULT_REPLY


def cancel_help_message() -> str:
    return (
        "❌ *Cancel Appointment*\n\n"
        "Please send your cancellation details like this:\n\n"
        "Name, Appointment Date\n\n"
        "Example:\nRavi Kumar, 5 July"
    )


def finish_cancellation(phone: str, name: str, preferred_date: str) -> str:
    cancelled = cancel_appointment(phone, name, preferred_date)
    clear_state(phone)

    if cancelled:
        send_whatsapp(
            DOCTOR_WHATSAPP,
            f"❌ *Appointment Cancelled*\n\n"
            f"👤 Name: {cancelled.get('Name', name)}\n"
            f"📞 Phone: {phone}\n"
            f"📅 Date: {cancelled.get('Preferred Date', preferred_date)}\n"
            f"🕘 Time: {cancelled.get('Approved Time', '') or 'Not approved yet'}\n"
            f"Preferred Slot: {cancelled.get('Preferred Slot', '')}",
        )
        return (
            f"✅ Your appointment for *{preferred_date}* has been cancelled.\n\n"
            "To book again, reply *1*."
        )

    return (
        "⚠️ I could not find an active appointment with those details.\n\n"
        "Please check the name/date or reply *6* to talk to staff."
    )


# ─────────────────────────────────────
# DOCTOR FLOW HANDLERS
# ─────────────────────────────────────
def handle_doctor_pin(phone: str, msg: str, resp: MessagingResponse):
    """Doctor enters their PIN to unlock approve/reject commands."""
    if verify_doctor_pin(phone, msg):
        resp.message("✅ PIN verified. You can now use approve and reject commands.")
    else:
        resp.message("⛔ Wrong PIN. Please try again.")


def handle_approve(phone: str, incoming: str, resp: MessagingResponse):
if not is_doctor_number(phone):
    resp.message("⛔ Only the registered doctor number can approve appointments.")
    return
if not is_doctor_verified(phone):
    resp.message("🔐 Please verify your identity first.\nSend your doctor PIN to continue.")
    return

name, preferred_time, command_error = parse_approve_command(incoming)
if command_error:
    resp.message(f"⚠️ {command_error}")
    return

print(f"🔍 Approving: '{name}' at '{preferred_time}'")
patient_phone, appt_date, approved_time, approval_error = approve_appointment(name, preferred_time)
if patient_phone:
    send_whatsapp(
        f"whatsapp:{patient_phone}",
        f"✅ *Appointment Confirmed!*\n\nDear {name},\n"
        f"Your appointment at Sunshine Clinic is *approved* for:\n"
        f"📅 Date: {appt_date}\n"
        f"🕘 Time: {approved_time}\n\n"
        f"Please arrive 10 minutes early. See you soon! 🏥",
    )
    if patient_phone:
    send_whatsapp(
        f"whatsapp:{patient_phone}",
        f"✅ *Appointment Confirmed!* ...",
    )
    # ── NEW: also send SMS so patient gets it on their regular messages ──
    send_appointment_confirmation_sms(patient_phone, name, appt_date, approved_time)
    resp.message(...)
    resp.message(f"✅ Approved! Patient {name} notified for {appt_date} at {approved_time}.")
else:
    resp.message(f"⚠️ {approval_error}")


def handle_reject(phone: str, incoming: str, resp: MessagingResponse):
if not is_doctor_number(phone):
    resp.message("⛔ Only the registered doctor number can reject appointments.")
    return
if not is_doctor_verified(phone):
    resp.message("🔐 Please verify your identity first.\nSend your doctor PIN to continue.")
    return

name = clean(incoming[7:])
print(f"🔍 Rejecting: '{name}'")
patient_phone, appt_date = reject_appointment(name)
if patient_phone:
    set_state(patient_phone, "awaiting_reschedule")
    send_whatsapp(
        f"whatsapp:{patient_phone}",
        f"❌ *Appointment Update*\n\nDear {name},\n"
        f"The slot for {appt_date} is not available.\n\n"
        f"Please reply with a new preferred date in this format:\n"
        f"Name, Preferred Date, Reason",
    )
    if patient_phone:
    send_whatsapp(...)
    # ── NEW ──
    send_rejection_sms(patient_phone, name, appt_date)
    resp.message(...)
    resp.message(f"❌ Rejected. Patient {name} has been asked to reschedule.")
else:
    resp.message(f"⚠️ Could not find pending appointment for {name}.")


# ─────────────────────────────────────
# PATIENT FLOW HANDLERS
# ─────────────────────────────────────
def handle_cancel_trigger(phone: str, incoming: str, msg: str, resp: MessagingResponse):
    """Patient initiates a cancellation (menu option 5 or typing 'cancel ...')."""
    if msg.startswith("cancel "):
        cancel_text = incoming[7:].strip()
        parts = [p.strip() for p in cancel_text.split(",")]
        if len(parts) >= 2:
            resp.message(finish_cancellation(phone, clean(parts[0]), clean(parts[1])))
            return
    set_state(phone, "awaiting_cancel_details")
    resp.message(cancel_help_message())


def handle_cancel_details(phone: str, incoming: str, resp: MessagingResponse):
    """Patient provides Name, Date after being prompted."""
    parts = [p.strip() for p in incoming.split(",")]
    if len(parts) >= 2:
        resp.message(finish_cancellation(phone, clean(parts[0]), clean(parts[1])))
    else:
        resp.message(cancel_help_message())


def handle_booking_start(phone: str, resp: MessagingResponse):
    set_state(phone, "awaiting_booking")
    resp.message(
        "📅 *Book an Appointment*\n\n"
        "Please share details in ONE message:\n\n"
        "• Full name\n"
        "• Preferred date (e.g. 5 July)\n"
        "• Reason for visit\n\n"
        "Example:\nRavi Kumar, 5 July, Fever and cold"
    )


def handle_booking_details(phone: str, incoming: str, current_date: str, resp: MessagingResponse):
    """Patient sends Name, Date, Reason."""
    parts = [p.strip() for p in incoming.split(",")]
    if len(parts) < 3:
        resp.message(
            "⚠️ Please share in this format:\n\n"
            "Name, Preferred Date, Reason\n\n"
            "Example:\nRavi Kumar, 5 July, Fever and cold"
        )
        return

    name = clean(parts[0])
    preferred_date = clean(parts[1])
    reason = ", ".join(parts[2:]).strip()

    if is_day_full(preferred_date):
        resp.message(
            f"⚠️ Sorry, *{preferred_date}* is fully booked.\n\n"
            "Please reply with a different date.\n\n"
            "Example:\nRavi Kumar, 6 July, Fever and cold"
        )
        return

    set_pending_booking(phone, {"name": name, "date": preferred_date, "reason": reason, "booked_on": current_date})
    set_state(phone, "awaiting_slot")
    resp.message(
        f"✅ Got it {name}!\n\n"
        f"Please choose a preferred time slot for *{preferred_date}*:\n\n"
        f"{format_available_slot_menu(preferred_date)}"
    )


def handle_slot_selection(phone: str, msg: str, current_date: str, resp: MessagingResponse):
    """Patient picks a slot number from the dynamic menu."""
    booking = get_pending_booking(phone)
    preferred_date = booking.get("date", "")
    slot = get_slot_from_patient_choice(preferred_date, msg.strip())

    if not slot:
        resp.message("⚠️ Please choose one of the available slot numbers shown above.")
        return

    name = booking.get("name", "")
    reason = booking.get("reason", "")
    booked_on = booking.get("booked_on", current_date)
    remaining_times = get_remaining_times_for_slot(preferred_date, slot)

    if not remaining_times:
        if is_day_full(preferred_date):
            set_state(phone, "awaiting_booking")
            clear_pending_booking(phone)
            resp.message(
                f"⚠️ Sorry, *{preferred_date}* just became fully booked.\n\n"
                "Please send a different date in this format:\n"
                "Name, Preferred Date, Reason"
            )
        else:
            resp.message(
                f"⚠️ Sorry, that slot just became full for *{preferred_date}*.\n\n"
                "Please choose from the remaining slots:\n\n"
                f"{format_available_slot_menu(preferred_date)}"
            )
        return

    save_appointment(name, phone, preferred_date, slot, reason, booked_on)
    clear_state(phone)
    clear_pending_booking(phone)

    send_whatsapp(
        DOCTOR_WHATSAPP,
        f"🏥 *New Appointment Request*\n\n"
        f"👤 Name: {name}\n"
        f"📞 Phone: {phone}\n"
        f"📅 Date: {preferred_date}\n"
        f"🕘 Preferred Slot: {SLOT_LABELS[slot]}\n"
        f"🩺 Reason: {reason}\n\n"
        f"{format_available_times(slot, remaining_times)}\n\n"
        f"Reply with exact time to approve:\n"
        f"approve {name} {remaining_times[0]}\n"
        f"reject {name}",
    )
    resp.message(
        f"✅ Thank you {name}!\n\n"
        f"Your request for *{preferred_date}* ({slot}) has been received.\n\n"
        f"We will confirm your exact time within 1 hour. 🏥"
    )


# ─────────────────────────────────────
# MAIN WEBHOOK
# ─────────────────────────────────────
@app.route("/bot", methods=["POST"])
@validate_twilio_request
def bot():
    incoming  = request.form.get("Body", "").strip()
    raw_phone = request.form.get("From", "")
    phone     = normalize_whatsapp_number(raw_phone)
    now       = datetime.now()
    current_date = now.strftime("%d/%m/%Y")
    current_time = now.strftime("%I:%M %p")

    print(f"📨 Message from {phone}: {incoming}")
    print(f"🔍 State: {get_state(phone)}")

    # Guard: ignore empty messages
    if not incoming:
        return ""

    # Guard: reject suspiciously long messages
    if len(incoming) > 500:
        resp = MessagingResponse()
        resp.message("⚠️ Message too long. Please keep it under 500 characters.")
        return str(resp)

    save_lead(phone, incoming, current_date, current_time)

    resp = MessagingResponse()
    msg  = incoming.strip().lower()

    # ── Doctor PIN verification ──
    if is_doctor_number(phone) and msg.isdigit() and len(msg) == 4:
        handle_doctor_pin(phone, msg, resp)
        return str(resp)

    # ── Doctor commands ──
    if msg.startswith("approve "):
        handle_approve(phone, incoming, resp)
        return str(resp)

    if msg.startswith("reject "):
        handle_reject(phone, incoming, resp)
        return str(resp)

    # ── Cancel triggers ──
    if msg.startswith("cancel ") or msg in ["5", "cancel", "cancel appointment", "cancel booking"]:
        handle_cancel_trigger(phone, incoming, msg, resp)
        return str(resp)

    # ── Active conversation states ──
    state = get_state(phone)

    if state == "awaiting_cancel_details":
        handle_cancel_details(phone, incoming, resp)
        return str(resp)

    if msg == "1":
        handle_booking_start(phone, resp)
        return str(resp)

    if state in ["awaiting_booking", "awaiting_reschedule"]:
        handle_booking_details(phone, incoming, current_date, resp)
        return str(resp)

    if state == "awaiting_slot":
        handle_slot_selection(phone, msg, current_date, resp)
        return str(resp)

    # ── FAQ fallback ──
    resp.message(get_faq_reply(incoming))
    return str(resp)


# ─────────────────────────────────────
# RUN
# ─────────────────────────────────────
# ── /sms-reply — inbound SMS webhook (Stage 3) ──
app.add_url_rule(
"/sms-reply",
"sms_reply",
validate_twilio_request(build_sms_reply_handler(cancel_appointment)),
methods=["POST"],
)
if __name__ == "__main__":
print("🤖 Sunshine Clinic Bot running on http://localhost:8080")
app.run(port=8080, debug=True)  