from enum import Enum


class PaymentSource(str, Enum):
    MANUAL = "MANUAL"
    WHATSAPP_AI = "WHATSAPP_AI"
    API = "API"