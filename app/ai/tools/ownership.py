"""Shared tenant-ownership guard for read-only assistant tools.

Every tool that reaches contract-scoped data first confirms the contract belongs
to the requesting user, so the assistant can never read across tenants -- even
though the underlying reporting/payment services are contract-id based.
"""


def owned_contract(contract_service, contract_id: int, user_id: int):
    """Return the contract if owned by ``user_id``, else None."""

    contract = contract_service.get_contract(contract_id)

    if contract is None or contract.user_id != user_id:
        return None

    return contract
