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

        # Nothing to update if no payment was created
        if state.payment_id is None:
            return state

        contract = self.contract_service.get_contract(
            state.contract_id
        )

        if contract is None:
            return state

        state.total_amount = contract.total_amount
        state.daily_amount = contract.daily_amount

        state.total_paid = self.payment_service.calculate_total_paid(
            state.contract_id
        )

        state.remaining_amount = self.payment_service.calculate_remaining_amount(
            contract.total_amount,
            state.contract_id,
        )

        return state
