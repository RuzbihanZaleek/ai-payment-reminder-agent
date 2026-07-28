"""Insight tools delegate to exactly one service and perform no calculations."""

from app.ai.tools import (
    FinancialInsightTool,
    ContractInsightTool,
    PaymentInsightTool,
    SchedulerInsightTool,
    RecommendationTool,
)


class Spy:
    def __init__(self, **returns):
        self.returns = returns
        self.calls = []

    def __getattr__(self, name):
        def _method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            return self.returns.get(name, [])
        return _method


def test_financial_tool_delegates():
    svc = Spy(
        get_financial_summary={"collection_rate": 0.5},
        get_roi_summary={"collected": 1},
        get_cashflow_summary={"outstanding": 2},
    )
    out = FinancialInsightTool(svc).get_financial_overview(7)

    assert out["summary"] == {"collection_rate": 0.5}
    assert {c[0] for c in svc.calls} == {
        "get_financial_summary", "get_roi_summary", "get_cashflow_summary"
    }
    # user_id forwarded.
    assert all(c[1] == (7,) for c in svc.calls)


def test_contract_tool_delegates():
    svc = Spy()
    ContractInsightTool(svc).get_contract_overview(7)
    called = {c[0] for c in svc.calls}
    assert "get_overdue_contracts" in called
    assert "get_contracts_near_completion" in called


def test_payment_tool_delegates():
    svc = Spy(get_payment_summary={"payment_count": 0})
    out = PaymentInsightTool(svc).get_payment_overview(7)
    assert out["summary"] == {"payment_count": 0}


def test_scheduler_tool_delegates():
    svc = Spy(get_reminder_statistics={"total_scheduler_runs": 0})
    out = SchedulerInsightTool(svc).get_reminder_overview(7)
    assert out["statistics"] == {"total_scheduler_runs": 0}


def test_recommendation_tool_delegates():
    svc = Spy(generate=["No contracts appear overdue."])
    out = RecommendationTool(svc).get_recommendations(7)
    assert out["recommendations"] == ["No contracts appear overdue."]
    assert svc.calls[0] == ("generate", (7,), {})
