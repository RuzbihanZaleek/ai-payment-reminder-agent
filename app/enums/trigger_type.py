from enum import Enum


class TriggerType(str, Enum):
    MESSAGE = "MESSAGE"
    SCHEDULED_REMINDER = "SCHEDULED_REMINDER"
