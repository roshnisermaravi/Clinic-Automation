# ─────────────────────────────────────
# APPOINTMENTS.PY — Booking, Approval, Rejection, Cancellation Logic
# ─────────────────────────────────────
import re
from datetime import datetime
from threading import Lock

from sheets import get_all_appointments, update_appointment_cell

approval_lock = Lock()

# ─────────────────────────────────────
# SLOT CONSTANTS
# ─────────────────────────────────────
TIME_SLOTS = {
    "1": "Morning",
    "2": "Afternoon",
    "3": "Evening",
}

SLOT_TIMES = {
    "Morning":   ["9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM"],
    "Afternoon": ["1:00 PM", "1:30 PM", "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM", "4:00 PM", "4:30 PM"],
    "Evening":   ["5:00 PM", "5:30 PM", "6:00 PM", "6:30 PM", "7:00 PM", "7:30 PM"],
}

SLOT_LABELS = {
    "Morning":   "Morning (9am – 1pm)",
    "Afternoon": "Afternoon (1pm – 5pm)",
    "Evening":   "Evening (5pm – 8pm)",
}


# ─────────────────────────────────────
# NORMALIZERS
# ─────────────────────────────────────
def clean(text: str) -> str:
    return text.strip().strip("_").strip("*").strip()


def normalize_date(preferred_date: str) -> str:
    return clean(preferred_date).lower()


def normalize_slot(slot: str) -> str:
    cleaned = clean(slot).lower()
    for slot_name in SLOT_TIMES:
        if cleaned == slot_name.lower():
            return slot_name
    return ""


def normalize_time(time_text: str) -> str:
    """Convert doctor-entered times like 10am or 10:30 AM into one standard format."""
    cleaned = " ".join(clean(time_text).upper().replace(".", "").split())
    cleaned = re.sub(r"(\d)(AM|PM)$", r"\1 \2", cleaned)
    for time_format in ("%I:%M %p", "%I %p"):
        try:
            return datetime.strptime(cleaned, time_format).strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
    return ""


def normalize_whatsapp_number(phone: str) -> str:
    return phone.replace("whatsapp:", "").strip()


# ─────────────────────────────────────
# CONFLICT DETECTION
# ─────────────────────────────────────
def _is_approved(record: dict) -> bool:
    return record.get("Status", "").strip().lower() == "approved"


def get_approved_times_for_date(preferred_date: str) -> set:
    """Only approved appointments block exact times."""
    approved_times = set()
    for record in get_all_appointments():
        same_date = normalize_date(record.get("Preferred Date", "")) == normalize_date(preferred_date)
        approved_time = normalize_time(record.get("Approved Time", ""))
        if same_date and _is_approved(record) and approved_time:
            approved_times.add(approved_time)
    return approved_times


def get_available_times(preferred_date: str) -> dict:
    """Return every remaining exact time grouped by slot."""
    approved_times = get_approved_times_for_date(preferred_date)
    return {
        slot_name: [t for t in times if t not in approved_times]
        for slot_name, times in SLOT_TIMES.items()
    }


def get_remaining_times_for_slot(preferred_date: str, preferred_slot: str) -> list:
    slot_name = normalize_slot(preferred_slot)
    if not slot_name:
        return []
    return get_available_times(preferred_date).get(slot_name, [])


def get_available_slots(preferred_date: str) -> list:
    """Return only slots that still have at least one free time."""
    return [
        slot_name
        for slot_name, times in get_available_times(preferred_date).items()
        if times
    ]


def is_day_full(preferred_date: str) -> bool:
    return not get_available_slots(preferred_date)


def is_time_available(preferred_date: str, approved_time: str) -> bool:
    time_value = normalize_time(approved_time)
    if not time_value:
        return False
    return time_value not in get_approved_times_for_date(preferred_date)


# ─────────────────────────────────────
# MENU BUILDERS
# ─────────────────────────────────────
def format_available_slot_menu(preferred_date: str) -> str:
    """Build the numbered slot menu shown to patients, hiding full slots."""
    available_slots = get_available_slots(preferred_date)
    lines = []
    option_number = 1
    for slot_key in ["1", "2", "3"]:
        slot_name = TIME_SLOTS[slot_key]
        if slot_name in available_slots:
            lines.append(f"{option_number}️⃣ {SLOT_LABELS[slot_name]}")
            option_number += 1
    return "\n".join(lines)


def get_slot_from_patient_choice(preferred_date: str, choice: str) -> str:
    """Convert the patient's dynamic menu number into a slot name."""
    available_slots = get_available_slots(preferred_date)
    try:
        index = int(choice.strip()) - 1
    except ValueError:
        return ""
    if 0 <= index < len(available_slots):
        return available_slots[index]
    return ""


def format_available_times(slot_name: str, times: list) -> str:
    """Build the exact-time list shown to the doctor."""
    if not times:
        return f"Available {slot_name} Times\nNo times available"
    return f"Available {slot_name} Times\n" + "\n".join(times)


# ─────────────────────────────────────
# DOCTOR COMMAND PARSING
# ─────────────────────────────────────
def parse_approve_command(incoming: str):
    """
    Parse 'approve Ravi Kumar 10:30 AM' into (name, time, error).
    Returns (name, approved_time, "") on success.
    Returns ("", "", error_message) on failure.
    """
    command_text = clean(incoming[8:])
    match = re.match(r"^(.+?)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm))$", command_text, re.IGNORECASE)
    if not match:
        return "", "", "Use this format:\napprove Patient Name 10:30 AM"

    name = clean(match.group(1))
    approved_time = normalize_time(match.group(2))

    if not approved_time:
        return "", "", "Use this format:\napprove Patient Name 10:30 AM"
    if not name:
        return "", "", "Please include the patient name before the time."

    return name, approved_time, ""


def validate_doctor_time(record: dict, preferred_time: str):
    """
    Validate a doctor's approval time before writing it.
    Returns (True, approved_time, "") on success.
    Returns (False, "", error_message) on failure.
    """
    approved_time = normalize_time(preferred_time)
    preferred_slot = normalize_slot(record.get("Preferred Slot", ""))
    preferred_date = record.get("Preferred Date", "")

    if not approved_time:
        return False, "", "Please use a valid time like *10:30 AM*."

    if not preferred_slot:
        return False, "", "This appointment has an invalid preferred slot in the sheet."

    if approved_time not in SLOT_TIMES[preferred_slot]:
        available = get_remaining_times_for_slot(preferred_date, preferred_slot)
        available_text = "\n".join(available) if available else "No times available"
        return (
            False, "",
            f"*{approved_time}* is outside the patient's selected *{preferred_slot}* slot.\n\n"
            f"Available {preferred_slot} times:\n{available_text}",
        )

    if not is_time_available(preferred_date, approved_time):
        available = get_remaining_times_for_slot(preferred_date, preferred_slot)
        available_text = "\n".join(available) if available else "No times available"
        return (
            False, "",
            f"*{approved_time}* on *{preferred_date}* is already approved for another patient.\n\n"
            f"Available {preferred_slot} times:\n{available_text}",
        )

    return True, approved_time, ""


# ─────────────────────────────────────
# APPOINTMENT LOOKUP
# ─────────────────────────────────────
def find_pending_appointment_by_name(name: str):
    """
    Find one pending appointment by patient name.
    Returns (record, "") on success.
    Returns (None, error_message) if not found or ambiguous.
    """
    matches = [
        record for record in get_all_appointments()
        if clean(record.get("Name", "")).lower() == clean(name).lower()
        and record.get("Status", "").strip().lower() == "pending"
    ]

    if len(matches) == 1:
        return matches[0], ""

    if len(matches) > 1:
        details = [
            f"- {r.get('Name', '')}, {r.get('Preferred Date', '')}, {r.get('Phone', '')}"
            for r in matches[:5]
        ]
        return None, "Multiple pending appointments matched:\n" + "\n".join(details)

    return None, f"Could not find a pending appointment for {name}."


# ─────────────────────────────────────
# APPROVE / REJECT / CANCEL
# ─────────────────────────────────────
def approve_appointment(name: str, preferred_time: str):
    """
    Approve one pending appointment after conflict and slot validation.
    Returns (patient_phone, appt_date, approved_time, "") on success.
    Returns (None, None, "", error_message) on failure.
    """
    try:
        with approval_lock:
            record, lookup_error = find_pending_appointment_by_name(name)
            if lookup_error:
                return None, None, "", lookup_error

            valid, approved_time, validation_error = validate_doctor_time(record, preferred_time)
            if not valid:
                return None, None, "", validation_error

            row_num = record["_row"]
            update_appointment_cell(row_num, "Approved Time", approved_time)
            update_appointment_cell(row_num, "Status", "Approved")
            print(f"✅ Approved row {row_num} at {approved_time}")
            return (
                record.get("Phone", "").strip(),
                record.get("Preferred Date", "").strip(),
                approved_time,
                "",
            )
    except Exception as e:
        print(f"⚠️ Approve error: {e}")
    return None, None, "", "Something went wrong while approving this appointment."


def reject_appointment(name: str):
    """
    Reject one pending appointment by name.
    Returns (patient_phone, appt_date) on success, (None, None) on failure.
    """
    try:
        for record in get_all_appointments():
            rec_name = clean(record.get("Name", ""))
            rec_status = record.get("Status", "").strip().lower()
            if rec_name.lower() == clean(name).lower() and rec_status == "pending":
                row_num = record["_row"]
                update_appointment_cell(row_num, "Status", "Rejected")
                print(f"✅ Rejected row {row_num}")
                return record.get("Phone", "").strip(), record.get("Preferred Date", "").strip()
    except Exception as e:
        print(f"⚠️ Reject error: {e}")
    return None, None


def cancel_appointment(phone: str, name: str = "", preferred_date: str = ""):
    """
    Cancel the most recent active appointment for a phone number.
    Optionally filters by name and date for precision.
    Returns the cancelled record dict, or None if not found.
    """
    try:
        for record in reversed(get_all_appointments()):
            same_phone = (
                normalize_whatsapp_number(record.get("Phone", ""))
                == normalize_whatsapp_number(phone)
            )
            active = record.get("Status", "").strip().lower() in ["pending", "approved"]
            name_ok = not name or clean(record.get("Name", "")).lower() == clean(name).lower()
            date_ok = not preferred_date or (
                normalize_date(record.get("Preferred Date", "")) == normalize_date(preferred_date)
            )

            if same_phone and active and name_ok and date_ok:
                row_num = record["_row"]
                update_appointment_cell(row_num, "Status", "Cancelled")
                print(f"✅ Cancelled row {row_num}")
                return record
    except Exception as e:
        print(f"⚠️ Cancel error: {e}")
    return None