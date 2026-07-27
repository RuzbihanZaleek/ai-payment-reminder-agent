from app.agents.contract_resolver_node import ContractResolverNode
from app.agents.state import AgentState


def _available():

    return [
        {"id": 1, "reference_code": "INV001"},
        {"id": 2, "reference_code": "INV002"},
    ]


def test_single_contract_auto_resolves_without_reference():

    node = ContractResolverNode()

    # One active contract, message has NO reference code -> auto-resolve.
    state = AgentState(
        message="I paid 100 today",
        requires_approval=False,
        resolved_contracts=[{"id": 5, "reference_code": "INV001"}],
    )

    result = node.execute(state)

    assert result.contract_id == 5
    assert result.contract_ids == [5]
    assert result.requires_approval is False


def test_resolves_explicit_reference():

    node = ContractResolverNode()

    state = AgentState(
        message="Paid INV001 $10",
        requires_approval=False,
        resolved_contracts=_available(),
    )

    result = node.execute(state)

    assert result.contract_ids == [1]
    assert result.contract_id == 1
    assert result.requires_approval is False


def test_unknown_reference_defers_to_allocation():

    node = ContractResolverNode()

    state = AgentState(
        message="Paid INV999 $10",
        requires_approval=False,
        resolved_contracts=_available(),
    )

    result = node.execute(state)

    # No matching reference -> don't resolve, don't force approval here;
    # automatic allocation happens downstream.
    assert result.contract_ids == []
    assert result.contract_id is None
    assert result.requires_approval is False


def test_no_reference_defers_to_allocation():

    node = ContractResolverNode()

    state = AgentState(
        message="I paid 100 today",
        requires_approval=False,
        resolved_contracts=_available(),
    )

    result = node.execute(state)

    assert result.contract_ids == []
    assert result.contract_id is None
    assert result.requires_approval is False


def test_ambiguous_multiple_references_requires_approval():

    node = ContractResolverNode()

    state = AgentState(
        message="Paid INV001 and INV002",
        requires_approval=False,
        resolved_contracts=_available(),
    )

    result = node.execute(state)

    assert set(result.contract_ids) == {1, 2}
    assert result.contract_id is None
    assert result.requires_approval is True


def test_no_available_contracts_is_noop():

    node = ContractResolverNode()

    # e.g. the direct /agent/messages path with an explicit contract_id.
    state = AgentState(
        message="Paid INV001 $10",
        contract_id=42,
        requires_approval=False,
        resolved_contracts=[],
    )

    result = node.execute(state)

    assert result.contract_id == 42
    assert result.contract_ids == []
    assert result.requires_approval is False