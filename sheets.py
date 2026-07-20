# ─────────────────────────────────────
# SHEETS.PY — Google Sheets Read / Write
# ─────────────────────────────────────
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Clinic Leads")

_scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# ── Lazy singletons — not created until first use ──
_gc           = None
_leads        = None
_appointments = None
_column_cache: dict = {}


def _connect():
    """
    Connect to Google Sheets on first use.
    Raises a clear RuntimeError if credentials are missing,
    instead of crashing the whole app at import time.
    """
    global _gc, _leads, _appointments

    if _leads is not None:
        return  # already connected

    if not os.path.exists(GOOGLE_CREDENTIALS_FILE):
        raise RuntimeError(
            f"Google credentials file not found: {GOOGLE_CREDENTIALS_FILE}\n"
            f"Add it to your project or set GOOGLE_CREDENTIALS_FILE in .env"
        )

    creds         = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, _scope)
    _gc           = gspread.authorize(creds)
    _leads        = _gc.open(GOOGLE_SHEET_NAME).sheet1
    _appointments = _gc.open(GOOGLE_SHEET_NAME).worksheet("Appointments")
    print("✅ Google Sheets connected.")


# ─────────────────────────────────────
# LEADS
# ─────────────────────────────────────
def save_lead(phone: str, message: str, date: str, time_str: str):
    """Save a new lead. Skips if the phone number already exists."""
    try:
        _connect()
        all_phones = _leads.col_values(1)
        if phone not in all_phones:
            _leads.append_row([phone, message, date, time_str, "New"])
            print("✅ New lead saved!")
        else:
            print("ℹ️ Existing customer — not saving again.")
    except Exception as e:
        print(f"⚠️ Lead save error: {e}")


# ─────────────────────────────────────
# APPOINTMENTS — READ
# ─────────────────────────────────────
def get_all_appointments() -> list[dict]:
    """
    Read all appointment rows from the sheet.
    Returns a list of dicts with an extra '_row' key for the actual sheet row number.

    ⚠️  Reads the full sheet on every call.
    TODO (Stage 5): Cache with a short TTL or move to PostgreSQL.
    """
    try:
        _connect()
        all_rows = _appointments.get_all_values()
        if len(all_rows) <= 1:
            return []

        headers = [h.strip() for h in all_rows[0]]
        records = []
        for i, row in enumerate(all_rows[1:], start=2):
            record = {"_row": i}
            for j, header in enumerate(headers):
                record[header] = row[j] if j < len(row) else ""
            records.append(record)
        return records
    except Exception as e:
        print(f"⚠️ Get appointments error: {e}")
        return []


# ─────────────────────────────────────
# APPOINTMENTS — WRITE
# ─────────────────────────────────────
def save_appointment(
    name: str,
    phone: str,
    preferred_date: str,
    preferred_slot: str,
    reason: str,
    booked_on: str,
):
    """Append a new pending appointment row."""
    try:
        _connect()
        _appointments.append_row(
            [name, phone, preferred_date, preferred_slot, "", reason, booked_on, "Pending"]
        )
        print("✅ Appointment saved!")
    except Exception as e:
        print(f"⚠️ Appointment save error: {e}")


def update_appointment_cell(row_num: int, header_name: str, value: str) -> bool:
    """Update a single cell by row number and column header name."""
    column_num = _get_column_number(header_name)
    if not column_num:
        return False
    try:
        _connect()
        _appointments.update_cell(row_num, column_num, value)
        return True
    except Exception as e:
        print(f"⚠️ Cell update error: {e}")
        return False


def _get_column_number(header_name: str):
    """
    Return the 1-based column index for a header name.
    Cached after first call to avoid repeated sheet reads.
    """
    if header_name in _column_cache:
        return _column_cache[header_name]
    try:
        _connect()
        headers = [h.strip() for h in _appointments.row_values(1)]
        index = headers.index(header_name) + 1
        _column_cache[header_name] = index
        return index
    except ValueError:
        print(f"⚠️ Missing column in Appointments sheet: {header_name}")
    except Exception as e:
        print(f"⚠️ Column lookup error: {e}")
    return None