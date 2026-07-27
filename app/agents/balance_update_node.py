from decimal import Decimal

from app.agents.state import AgentState
from app.services.payment_service import PaymentService
from app.services.contract_service import ContractService


class BalanceUpdateNode:

    def __init__(
        self,
        payment_service: PaymentService,
        contract_service: ContractService,
    ):
        self.payment_service = payment_service
        self.contract_service = contract_service

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        # Nothing to update if no payment was created.
        if state.payment_id is None:
            return state

        # Every contract that received an allocation must be refreshed. Fall
        # back to the single resolved contract when no allocations are present.
        affected_ids = [
            allocation["contract_id"]
            for allocation in state.payment_allocations
        ]

        if not affected_ids and state.contract_id is not None:
            affected_ids = [state.contract_id]

        if not affected_ids:
            return state

        total_amount = Decimal("0")
        total_paid = Decimal("0")
        remaining_amount = Decimal("0")
        daily_amount = None
        whatsapp_chat_id = None

        for contract_id in affected_ids:
            contract = self.contract_service.get_contract(contract_id)

            if contract is None:
                continue

            total_amount += contract.total_amount
            total_paid += self.payment_service.calculate_total_paid(contract_id)
            remaining_amount += self.payment_service.calculate_remaining_amount(
                contract.total_amount,
                contract_id,
            )

            if daily_amount is None:
                daily_amount = contract.daily_amount
                whatsapp_chat_id = contract.whatsapp_chat_id

        state.total_amount = total_amount
        state.total_paid = total_paid
        state.remaining_amount = remaining_amount
        state.daily_amount = daily_amount
        state.whatsapp_chat_id = whatsapp_chat_id

        return state