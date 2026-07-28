"""WhatsApp phone-number validation/normalization.

Meta delivers the sender as digits only (e.g. "94771234567"). We normalize a
user-typed number to that form and validate it's a plausible international
number. Used so AI-created contracts always have a real WhatsApp number (never
a placeholder).
"""

import re


def normalize_phone(raw: str) -> str:
    """Strip everything but digits (drops '+', spaces, dashes, parentheses)."""

    return re.sub(r"\D", "", raw or "")


def is_valid_whatsapp_number(raw: str) -> bool:
    """A plausible international WhatsApp number: 8-15 digits."""

    digits = normalize_phone(raw)
    return 8 <= len(digits) <= 15
