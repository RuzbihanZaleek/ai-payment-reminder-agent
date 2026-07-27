from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.enums.payment_status import PaymentStatus
from app.enums.approval_status import ApprovalStatus
from app.core.errors import NotFoundError, ErrorCode
from app.schemas.pagination import Page, PaginationParams
from app.api.query_params import approval_status_param
from app.container import create_payment_approval_service
from app.services.payment_approval_service import PaymentApprovalService
from app.api.deps import get_current_user
from app.models.user import User


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


@router.get("/pending", response_model=Page[ApprovalResponse])
def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    approval_status: ApprovalStatus = Depends(approval_status_param),
    pagination: PaginationParams = Depends(),
    service: PaymentApprovalService = Depends(get_payment_approval_service),
):
    # Defaults to PENDING (preserving the endpoint's original meaning); an
    # optional ?status= lets a reviewer page through approved/rejected too.
    result = service.get_approvals_page(
        current_user.id,
        approval_status,
        pagination.page,
        pagination.page_size,
        pagination.order,
    )

    return Page.build(result, pagination.page, pagination.page_size)


@router.post("/{payment_id}/approve", response_model=ApprovalResponse)
def approve_payment(
    payment_id: int,
    request: ReviewRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentApprovalService = Depends(get_payment_approval_service),
):

    payment = service.approve_payment(
        payment_id=payment_id,
        approved_by=request.reviewed_by,
        user_id=current_user.id,
    )

    if payment is None:
        raise NotFoundError("Payment not found.", code=ErrorCode.PAYMENT_NOT_FOUND)

    return payment


@router.post("/{payment_id}/reject", response_model=ApprovalResponse)
def reject_payment(
    payment_id: int,
    request: ReviewRequest,
    current_user: User = Depends(get_current_user),
    service: PaymentApprovalService = Depends(get_payment_approval_service),
):

    payment = service.reject_payment(
        payment_id=payment_id,
        rejected_by=request.reviewed_by,
        user_id=current_user.id,
    )

    if payment is None:
        raise NotFoundError("Payment not found.", code=ErrorCode.PAYMENT_NOT_FOUND)

    return payment
