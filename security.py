# ─────────────────────────────────────
# SECURITY.PY — Webhook Verification & Doctor Identity
# ─────────────────────────────────────
import os
from functools import wraps

from flask import request, abort
from twilio.request_validator import RequestValidator

TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
DOCTOR_WHATSAPP = os.getenv("DOCTOR_WHATSAPP")

# A secret PIN the doctor must enter once per session to unlock approve/reject.
# Set this in your .env file as DOCTOR_PIN=1234 (choose your own).
DOCTOR_PIN = os.getenv("DOCTOR_PIN", "0000")

# In-memory set of verified doctor sessions.
# ⚠️  Resets on Flask restart — acceptable for now.
# TODO (Stage 5): Move to Redis with expiry for persistence.
verified_doctors: set = set()

_validator = RequestValidator(TWILIO_AUTH_TOKEN)


# ─────────────────────────────────────
# TWILIO WEBHOOK SIGNATURE VERIFICATION
# ─────────────────────────────────────
def validate_twilio_request(f):
    """
    Decorator — rejects any POST that did not come from Twilio.
    Twilio signs every request with your Auth Token.
    Anyone who discovers your URL cannot fake a valid signature.

    Usage:
        @app.route("/bot", methods=["POST"])
        @validate_twilio_request
        def bot():
            ...
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get("X-Twilio-Signature", "")
        url = request.url
        post_params = request.form.to_dict()

        if not _validator.validate(url, post_params, signature):
            print("⛔ Invalid Twilio signature — request rejected.")
            abort(403)

        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────
# DOCTOR IDENTITY
# ─────────────────────────────────────
def normalize_whatsapp_number(phone: str) -> str:
    return phone.replace("whatsapp:", "").strip()


def is_doctor_number(phone: str) -> bool:
    """Check if the phone number matches the registered doctor number."""
    return normalize_whatsapp_number(phone) == normalize_whatsapp_number(DOCTOR_WHATSAPP)


def is_doctor_verified(phone: str) -> bool:
    """
    Check if the doctor has completed PIN verification this session.
    Two-layer check: correct number AND correct PIN entered.
    """
    return phone in verified_doctors


def verify_doctor_pin(phone: str, entered_pin: str) -> bool:
    """
    Called when doctor sends their PIN.
    Returns True and marks them verified if PIN matches.
    """
    if entered_pin.strip() == DOCTOR_PIN:
        verified_doctors.add(phone)
        print(f"✅ Doctor {phone} verified with PIN.")
        return True
    print(f"⛔ Wrong PIN attempt from {phone}.")
    return False


def revoke_doctor_session(phone: str):
    """Optionally log out the doctor (e.g. if they send 'logout')."""
    verified_doctors.discard(phone)
    print(f"🔒 Doctor session revoked for {phone}.")