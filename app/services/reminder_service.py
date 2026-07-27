from app.models.contract import Contract
from app.services.contract_service import ContractService
from app.services.reminder_policy_service import ReminderPolicyService


class ReminderService:

    def __init__(
        self,
        contract_service: ContractService,
        reminder_policy_service: ReminderPolicyService,
    ):
        self.contract_service = contract_service
        self.reminder_policy_service = reminder_policy_service

    def get_pending_reminders(self) -> list[Contract]:

        return [
            contract
            for contract in self.contract_service.get_all_contracts()
            if self.reminder_policy_service.should_send_reminder(contract)
        ]
