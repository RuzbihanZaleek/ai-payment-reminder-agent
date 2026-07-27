from app.agents.state import AgentState


class ContractResolverNode:
    """Resolves which contract a message refers to via an explicit reference.

    This phase supports explicit selection only: the message must mention a
    contract's reference_code (e.g. "Paid INV001 $10"). It never guesses.
    """

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        available = state.resolved_contracts

        # No multi-contract context (e.g. the direct /agent/messages path with
        # an explicit contract_id) -> nothing to resolve.
        if not available:
            return state

        message = (state.message or "").lower()

        matched_ids = [
            contract["id"]
            for contract in available
            if self._is_referenced(message, contract)
        ]

        state.contract_ids = matched_ids

        if len(matched_ids) == 1:
            # Exactly one explicit reference -> resolved.
            state.contract_id = matched_ids[0]
        else:
            # Zero references (don't guess) or ambiguous -> needs a human.
            state.requires_approval = True

        return state

    @staticmethod
    def _is_referenced(message: str, contract: dict) -> bool:

        reference_code = (contract.get("reference_code") or "").lower()

        return bool(reference_code) and reference_code in message