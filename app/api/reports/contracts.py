from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.db.session import SessionLocal
from app.enums.payment_status import PaymentStatus
from app.enums.payment_source import PaymentSource
from app.enums.approval_status import ApprovalStatus
from app.container import (
    create_contract_reporting_service,
    create_payment_reporting_service,
    create_receipt_reporting_service,
)
from app.services.contract_reporting_service import ContractReportingService
from app.services.payment_reporting_service import PaymentReportingService
from app.services.receipt_reporting_service import ReceiptReportingService
from app.core.errors import NotFoundError, ErrorCode
from app.schemas.pagination import Page, PaginationParams
from app.repositories.filters import PaymentFilter
from app.api.query_params import payment_filter_params
from app.api.deps import require_owned_contract


router = APIRouter(prefix="/reports/contracts", tags=["reports"])


class ContractSummaryResponse(BaseModel):

    contract_id: int
    reference_code: str
    name: str
    total_amount: Decimal
    total_paid: Decimal
    remaining_amount: Decimal
    payment_count: int


class PaymentReportResponse(BaseModel):

    id: int
    contract_id: int
    amount: Decimal
    payment_date: date
    status: PaymentStatus
    approval_status: ApprovalStatus
    source: PaymentSource
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceiptReportResponse(BaseModel):

    id: int
    contract_id: int
    payment_id: int
    amount: Decimal
    previous_balance: Decimal
    new_balance: Decimal
    allocation_summary: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


def get_contract_reporting_service():

    db = SessionLocal()

    try:
        yield create_contract_reporting_service(db=db)
    finally:
        db.close()


def get_payment_reporting_service():

    db = SessionLocal()

    try:
        yield create_payment_reporting_service(db=db)
    finally:
        db.close()


def get_receipt_reporting_service():

    db = SessionLocal()

    try:
        yield create_receipt_reporting_service(db=db)
    finally:
        db.close()


@router.get("/{contract_id}", response_model=ContractSummaryResponse)
def get_contract_summary(
    contract_id: int,
    contract=Depends(require_owned_contract),
    service: ContractReportingService = Depends(get_contract_reporting_service),
):

    summary = service.get_contract_summary(contract_id, contract.user_id)

    if summary is None:
        raise NotFoundError("Contract not found.", code=ErrorCode.CONTRACT_NOT_FOUND)

    return summary


@router.get("/{contract_id}/payments", response_model=Page[PaymentReportResponse])
def get_contract_payments(
    contract_id: int,
    contract=Depends(require_owned_contract),
    pagination: PaginationParams = Depends(),
    payment_filter: PaymentFilter = Depends(payment_filter_params),
    service: PaymentReportingService = Depends(get_payment_reporting_service),
):

    result = service.get_payment_history(
        contract_id,
        payment_filter,
        pagination.page,
        pagination.page_size,
        pagination.order,
    )

    return Page.build(result, pagination.page, pagination.page_size)


@router.get("/{contract_id}/receipts", response_model=Page[ReceiptReportResponse])
def get_contract_receipts(
    contract_id: int,
    contract=Depends(require_owned_contract),
    pagination: PaginationParams = Depends(),
    service: ReceiptReportingService = Depends(get_receipt_reporting_service),
):

    result = service.get_receipt_history(
        contract_id,
        pagination.page,
        pagination.page_size,
        pagination.order,
    )

    return Page.build(result, pagination.page, pagination.page_size)