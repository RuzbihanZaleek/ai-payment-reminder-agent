from enum import Enum

class PaymentIntent(str, Enum):

    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    NOT_PAYMENT = "NOT_PAYMENT"
    UNKNOWN = "UNKNOWN"