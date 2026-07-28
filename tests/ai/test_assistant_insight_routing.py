"""Deterministic routing of insight intents to the correct tools."""

from app.ai.assistant.intent import AssistantIntent, IntentDetectionResult
from app.ai.assistant.tools import AssistantToolExecutor


class _Tool:
    def __init__(self, **methods):
        for name, value in methods.items():
            setattr(self, name, (lambda v: (lambda *a, **k: v))(value))


def _executor():
    contract_tool = _Tool(get_active_contracts=[])
    return AssistantToolExecutor(
        contract_tool,
        _Tool(),  # payment_tool
        _Tool(),  # receipt_tool
        financial_insight_tool=_Tool(get_financial_overview={"summary": {"collection_rate": 0.9}}),
        contract_insight_tool=_Tool(get_contract_overview={"overdue": []}),
        payment_insight_tool=_Tool(
            get_payment_overview={"summary": {}},
            get_payment_trends={"trends": []},
            get_payers={"top_payers": []},
        ),
        scheduler_insight_tool=_Tool(get_reminder_overview={"statistics": {}}),
        recommendation_tool=_Tool(get_recommendations={"recommendations": ["ok"]}),
    )


def _gather(intent):
    return _executor().gather(IntentDetectionResult(intent=intent), user_id=7)


def test_financial_summary_routes_to_financial_tool():
    g = _gather(AssistantIntent.FINANCIAL_SUMMARY)
    assert "financial" in g["context"]
    assert "FinancialInsightTool.get_financial_overview" in g["tool_calls"]


def test_contract_analytics_routes_to_contract_tool():
    g = _gather(AssistantIntent.CONTRACT_ANALYTICS)
    assert "contracts" in g["context"]


def test_payment_analytics_routes_to_payment_tool():
    g = _gather(AssistantIntent.PAYMENT_ANALYTICS)
    assert "payments" in g["context"]


def test_payment_trends_routes_to_trends():
    g = _gather(AssistantIntent.PAYMENT_TRENDS)
    assert "payment_trends" in g["context"]


def test_reminder_analytics_routes_to_scheduler_tool():
    g = _gather(AssistantIntent.REMINDER_ANALYTICS)
    assert "reminders" in g["context"]
    assert "SchedulerInsightTool.get_reminder_overview" in g["tool_calls"]


def test_top_debtors_gathers_contracts_and_payers():
    g = _gather(AssistantIntent.TOP_DEBTORS)
    assert "contracts" in g["context"]
    assert "payers" in g["context"]


def test_monthly_report_combines_financial_and_trends():
    g = _gather(AssistantIntent.MONTHLY_REPORT)
    assert "financial" in g["context"]
    assert "payment_trends" in g["context"]


def test_recommendation_intent_gathers_broadly_with_recommendations():
    g = _gather(AssistantIntent.FINANCIAL_RECOMMENDATION)
    ctx = g["context"]
    assert "financial" in ctx and "contracts" in ctx and "payments" in ctx
    assert ctx["recommendations"] == ["ok"]
    assert "RecommendationTool.get_recommendations" in g["tool_calls"]


def test_insight_intents_do_not_break_without_tools():
    # Executor with no insight tools wired -> empty context, no crash.
    executor = AssistantToolExecutor(_Tool(get_active_contracts=[]), _Tool(), _Tool())
    g = executor.gather(IntentDetectionResult(intent=AssistantIntent.FINANCIAL_SUMMARY), user_id=7)
    assert g["context"] == {}
