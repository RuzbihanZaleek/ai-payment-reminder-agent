import re

from app.agents.state import AgentState


class ContractResolverNode:
    """Resolves which contract a message refers to via an explicit reference.

    Resolution outcomes:
      - Valid reference   -> resolve that contract.
      - Unknown reference -> requires approval (never auto-allocate).
      - No reference      -> defer to automatic payment allocation.
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

        if len(matched_ids) == 1:
            # Exactly one explicit, valid reference -> resolved.
            state.contract_ids = matched_ids
            state.contract_id = matched_ids[0]
            return state

        if len(matched_ids) > 1:
            # Ambiguous multiple references -> a human decides (out of scope).
            state.contract_ids = matched_ids
            state.contract_id = None
            state.requires_approval = True
            return state

        # No contract reference matched.
        state.contract_ids = []
        state.contract_id = None

        # A reference-like token that matches no contract is an unknown
        # reference -> require approval; never fall through to allocation.
        if self._mentions_unknown_reference(message, available):
            state.requires_approval = True
            return state

        # Genuinely no reference. A single contract is unambiguous, so
        # auto-resolve it; multiple contracts defer to automatic allocation.
        if len(available) == 1:
            contract_id = available[0]["id"]
            state.contract_id = contract_id
            state.contract_ids = [contract_id]

        return state

    @staticmethod
    def _is_referenced(message: str, contract: dict) -> bool:

        reference_code = (contract.get("reference_code") or "").lower()

        return bool(reference_code) and reference_code in message

    @staticmethod
    def _mentions_unknown_reference(message: str, available: list) -> bool:
        """True if the message contains a reference-like token (a known code's
        alphabetic prefix followed by digits) that matches no actual contract.
        """

        prefixes = set()

        for contract in available:
            code = (contract.get("reference_code") or "").lower()
            match = re.match(r"^([a-z]+)\d+$", code)

            if match:
                prefixes.add(match.group(1))

        for prefix in prefixes:
            if re.search(rf"{re.escape(prefix)}\d+", message):
                return True

        return False