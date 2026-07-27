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

        # Rule 1: no multi-contract context (e.g. the direct /agent/messages
        # path with an explicit contract_id) -> nothing to resolve.
        if not available:
            return state

        # Rule 2: exactly one active contract -> unambiguous, auto-resolve
        # without requiring approval (no reference code needed).
        if len(available) == 1:
            contract_id = available[0]["id"]
            state.contract_id = contract_id
            state.contract_ids = [contract_id]

            return state

        # Rule 3: multiple contracts -> require an explicit, unambiguous
        # reference. Never guess here; automatic allocation happens downstream.
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
        elif len(matched_ids) > 1:
            # Ambiguous multiple references -> a human decides (out of scope).
            state.contract_id = None
            state.requires_approval = True
        else:
            # No reference at all -> defer to automatic payment allocation.
            # Clear any pre-set primary so the allocator isn't short-circuited.
            state.contract_id = None

        return state

    @staticmethod
    def _is_referenced(message: str, contract: dict) -> bool:

        reference_code = (contract.get("reference_code") or "").lower()

        return bool(reference_code) and reference_code in message