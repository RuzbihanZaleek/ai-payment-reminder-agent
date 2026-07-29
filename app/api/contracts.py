from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.container import create_contract_service
from app.schemas.contract import ContractCreate, ContractResponse
from app.services.contract_service import ContractService
from app.core.errors import ConflictError, ErrorCode
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/contracts", tags=["contracts"])


def get_contract_service():

    db = SessionLocal()

    try:
        yield create_contract_service(db=db)
    finally:
        db.close()


@router.post(
    "",
    response_model=ContractResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contract(
    payload: ContractCreate,
    current_user: User = Depends(get_current_user),
    service: ContractService = Depends(get_contract_service),
) -> ContractResponse:
    """Create a contract owned by the authenticated user.

    Thin router: the owner comes from the JWT, all validation lives in the
    ``ContractCreate`` schema, and the write (plus audit) is the service's job.
    Once the contract is ACTIVE the scheduled reminder engine picks it up
    automatically -- no further wiring needed.
    """

    try:
        contract = service.create_contract(payload, user_id=current_user.id)
    except IntegrityError:
        # The reference_code has a UNIQUE constraint; a clash is a client error.
        raise ConflictError(
            f"A contract with reference_code '{payload.reference_code}' "
            "already exists.",
            code=ErrorCode.INVALID_REFERENCE,
        )

    return ContractResponse.model_validate(contract)
