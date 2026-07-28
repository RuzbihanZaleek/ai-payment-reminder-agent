from app.core.phone import normalize_phone, is_valid_whatsapp_number


def test_normalize_strips_non_digits():
    assert normalize_phone("+94 77 123 4567") == "94771234567"
    assert normalize_phone("(077) 123-4567") == "0771234567"


def test_valid_numbers():
    assert is_valid_whatsapp_number("94771234567") is True
    assert is_valid_whatsapp_number("+94 77 123 4567") is True


def test_invalid_numbers():
    assert is_valid_whatsapp_number("123") is False          # too short
    assert is_valid_whatsapp_number("1234567890123456") is False  # too long
    assert is_valid_whatsapp_number("") is False
    assert is_valid_whatsapp_number("abc") is False
