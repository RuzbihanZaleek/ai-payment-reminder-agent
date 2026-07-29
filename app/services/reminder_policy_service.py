from datetime import date

from app.models.contract import Contract, ContractStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.reminder_log_repository import ReminderLogRepository
from app.services.payment_service import PaymentService


class ReminderPolicyService:

    def __init__(
        self,
        payment_service: PaymentService,
        payment_repository: PaymentRepository,
        reminder_log_repository: ReminderLogRepository,
    ):
        self.payment_service = payment_service
        self.payment_repository = payment_repository
        self.reminder_log_repository = reminder_log_repository

    def should_send_reminder(self, contract: Contract) -> bool:

        # 0. Only active, already-started contracts are reminded. A paused/
        # cancelled/completed contract, or one whose start date is in the
        # future, is never due a reminder.
        if contract.status != ContractStatus.ACTIVE:
            return False

        if contract.start_date is not None and contract.start_date > date.today():
            return False

        # 1. Nothing owed -> no reminder.
        remaining = self.payment_service.calculate_remaining_amount(
            contract.total_amount,
            contract.id,
        )

        if remaining == 0:
            return False

        # 2. Already paid something today -> no reminder.
        if self.payment_repository.has_payment_for_date(
            contract.id,
            date.today(),
        ):
            return False

        # 3. Already reminded today -> no duplicate reminder.
        if self.reminder_log_repository.has_sent_today(contract.id):
            return False

        # 4. Otherwise the contract is due a reminder.
        return True
