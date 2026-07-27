from decimal import Decimal

from app.services.dashboard_service import DashboardService


class FakeContractReporting:

    def __init__(self, stats):
        self.stats = stats

    def get_contract_stats(self):
        return self.stats


class FakePaymentReporting:

    def __init__(self, stats):
        self.stats = stats

    def get_payment_stats(self):
        return self.stats


class FakeAgentReporting:

    def __init__(self, stats):
        self.stats = stats

    def get_agent_stats(self):
        return self.stats


class FakeSchedulerReporting:

    def __init__(self, stats):
        self.stats = stats

    def get_scheduler_stats(self):
        return self.stats


def _service(contracts, payments, agents, scheduler):

    return DashboardService(
        FakeContractReporting(contracts),
        FakePaymentReporting(payments),
        FakeAgentReporting(agents),
        FakeSchedulerReporting(scheduler),
    )


def test_aggregates_all_sections():

    service = _service(
        contracts={
            "total_contracts": 5,
            "active_contracts": 3,
            "completed_contracts": 2,
            "total_remaining_amount": Decimal("1500"),
        },
        payments={"total_payments_received": 12, "pending_approval_count": 2},
        agents={"total_agent_runs": 20, "completed_runs": 18, "failed_runs": 2},
        scheduler={"total_scheduler_runs": 7, "successful_runs": 6, "failed_runs": 1},
    )

    overview = service.get_overview()

    assert overview["contracts"]["total_contracts"] == 5
    assert overview["contracts"]["total_remaining_amount"] == Decimal("1500")
    assert overview["payments"]["pending_approval_count"] == 2
    assert overview["agents"]["completed_runs"] == 18
    assert overview["scheduler"]["failed_runs"] == 1


def test_empty_data():

    zero_contracts = {
        "total_contracts": 0,
        "active_contracts": 0,
        "completed_contracts": 0,
        "total_remaining_amount": Decimal("0"),
    }

    service = _service(
        contracts=zero_contracts,
        payments={"total_payments_received": 0, "pending_approval_count": 0},
        agents={"total_agent_runs": 0, "completed_runs": 0, "failed_runs": 0},
        scheduler={"total_scheduler_runs": 0, "successful_runs": 0, "failed_runs": 0},
    )

    overview = service.get_overview()

    assert overview["contracts"]["total_contracts"] == 0
    assert overview["payments"]["total_payments_received"] == 0
    assert overview["agents"]["total_agent_runs"] == 0
    assert overview["scheduler"]["total_scheduler_runs"] == 0