"""Read-only approval tool for the assistant (SHOW_PENDING_APPROVALS).

Delegates to the existing PaymentApprovalService (tenant-scoped) -- never a
repository, and performs no calculations.
"""


class ApprovalTool:

    def __init__(self, payment_approval_service):
        self.payment_approval_service = payment_approval_service

    def get_pending_approvals(self, user_id: int) -> list[dict]:
        payments = self.payment_approval_service.get_pending_approvals(user_id)
        return [
            {
                "payment_id": p.id,
                "contract_id": p.contract_id,
                "amount": p.amount,
                "status": p.status.value if hasattr(p.status, "value") else p.status,
                "approval_status": (
                    p.approval_status.value
                    if hasattr(p.approval_status, "value")
                    else p.approval_status
                ),
            }
            for p in payments
        ]
