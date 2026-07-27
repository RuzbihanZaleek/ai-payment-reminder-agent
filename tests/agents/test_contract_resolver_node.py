from app.agents.contract_resolver_node import ContractResolverNode
from app.agents.state import AgentState


def _available():

    return [
        {"id": 1, "reference_code": "INV001"},
        {"id": 2, "reference_code": "INV002"},
    ]


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


def test_unknown_reference_requires_approval():

    node = ContractResolverNode()

    state = AgentState(
        message="Paid INV999 $10",
        requires_approval=False,
        resolved_contracts=_available(),
    )

    result = node.execute(state)

    assert result.contract_ids == []
    assert result.requires_approval is True


def test_no_reference_does_not_guess():

    node = ContractResolverNode()

    state = AgentState(
        message="I paid 100 today",
        requires_approval=False,
        resolved_contracts=_available(),
    )

    result = node.execute(state)

    assert result.contract_ids == []
    assert result.contract_id is None
    assert result.requires_approval is True


def test_ambiguous_multiple_references_requires_approval():

    node = ContractResolverNode()

    state = AgentState(
        message="Paid INV001 and INV002",
        requires_approval=False,
        resolved_contracts=_available(),
    )

    result = node.execute(state)

    assert set(result.contract_ids) == {1, 2}
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