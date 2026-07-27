from app.services.reminder_service import ReminderService


class FakeContract:

    def __init__(self, contract_id):
        self.id = contract_id


class FakeContractService:

    def __init__(self, contracts):
        self.contracts = contracts

    def get_all_contracts(self):

        return self.contracts


class FakeReminderPolicyService:
    """Approves only the contract ids it was configured with."""

    def __init__(self, approved_ids):
        self.approved_ids = approved_ids
        self.checked = []

    def should_send_reminder(self, contract):

        self.checked.append(contract.id)

        return contract.id in self.approved_ids


def test_returns_only_policy_approved_contracts():

    c1 = FakeContract(1)
    c2 = FakeContract(2)
    c3 = FakeContract(3)

    contract_service = FakeContractService([c1, c2, c3])
    policy = FakeReminderPolicyService(approved_ids={1, 3})

    service = ReminderService(contract_service, policy)

    result = service.get_pending_reminders()

    # Only the policy-approved contracts come back...
    assert result == [c1, c3]

    # ...and every contract was run through the policy.
    assert policy.checked == [1, 2, 3]


def test_no_contracts_when_policy_rejects_all():

    contract_service = FakeContractService([FakeContract(1), FakeContract(2)])
    policy = FakeReminderPolicyService(approved_ids=set())

    service = ReminderService(contract_service, policy)

    assert service.get_pending_reminders() == []
