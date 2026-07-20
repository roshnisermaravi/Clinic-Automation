# ─────────────────────────────────────
# STATE.PY — Conversation State Management
# ─────────────────────────────────────
# Holds in-memory state for active user conversations.
# ⚠️  These are plain dicts — they reset on every Flask restart.
# TODO (Stage 5): Replace with Redis or SQLite for persistence across restarts.

user_state: dict = {}
pending_booking: dict = {}


def get_state(phone: str):
    """Return the current conversation state for a user. None = no active flow."""
    return user_state.get(phone)


def set_state(phone: str, state):
    """Set the conversation state for a user."""
    user_state[phone] = state


def clear_state(phone: str):
    """Clear the conversation state for a user (flow completed or reset)."""
    user_state[phone] = None


def get_pending_booking(phone: str) -> dict:
    """Return the pending booking data for a user."""
    return pending_booking.get(phone, {})


def set_pending_booking(phone: str, data: dict):
    """Store partial booking data while user is mid-flow."""
    pending_booking[phone] = data


def clear_pending_booking(phone: str):
    """Remove pending booking once it is saved or cancelled."""
    pending_booking.pop(phone, None)