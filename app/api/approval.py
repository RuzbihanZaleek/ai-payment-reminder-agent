from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.container import create_payment_approval_service
from app.services.payment_approval_service import PaymentApprovalService


router = APIRouter(prefix="/approvals", tags=["approvals"])


class ReviewRequest(BaseModel):

    reviewed_by: str


class ApprovalResponse(BaseModel):

    id: int
    contract_id: int
    amount: Decimal
    status: PaymentStatus
    approval_status: ApprovalStatus

    model_config = ConfigDict(from_attributes=True)


def get_payment_approval_service():

    db = SessionLocal()

    try:
        yield create_payment_approval_service(db=db)
    finally:
        db.close()


@router.get("/pending", response_model=list[ApprovalResponse])
def list_pending_approvals(
    service: PaymentApprovalService = Depends(get_payment_approval_service),
):

    return service.get_pending_approvals()


@router.post("/{payment_id}/approve", response_model=ApprovalResponse)
def approve_payment(
    payment_id: int,
    request: ReviewRequest,
    service: PaymentApprovalService = Depends(get_payment_approval_service),
):

    payment = service.approve_payment(
        payment_id=payment_id,
        approved_by=request.reviewed_by,
    )

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment


@router.post("/{payment_id}/reject", response_model=ApprovalResponse)
def reject_payment(
    payment_id: int,
    request: ReviewRequest,
    service: PaymentApprovalService = Depends(get_payment_approval_service),
):

    payment = service.reject_payment(
        payment_id=payment_id,
        rejected_by=request.reviewed_by,
    )

    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment
