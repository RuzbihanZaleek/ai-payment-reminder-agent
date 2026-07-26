import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.contract_repository import ContractRepository
from app.services.agent_execution_service import AgentExecutionService
from app.api.agent import get_agent_execution_service


logger = logging.getLogger(__name__)

router = APIRouter(tags=["whatsapp"])


def get_contract_repository():

    db = SessionLocal()

    try:
        yield ContractRepository(db)
    finally:
        db.close()


def _extract_message(payload: dict):
    """Pull (message_id, sender_phone, body) out of a Meta webhook payload.

    Returns None for any event that is not a text message (status updates,
    malformed shapes, etc.).
    """

    try:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages")

                if not messages:
                    continue

                message = messages[0]

                message_id = message.get("id")
                phone = message.get("from")
                body = message.get("text", {}).get("body")

                if message_id and phone and body is not None:
                    return message_id, phone, body
    except (AttributeError, TypeError, IndexError):
        return None

    return None


@router.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
):

    if (
        hub_mode == "subscribe"
        and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN
    ):
        return PlainTextResponse(content=hub_challenge)

    raise HTTPException(status_code=403, detail="Invalid verification token")


@router.post("/webhook")
def receive_webhook(
    payload: dict = Body(...),
    contract_repository: ContractRepository = Depends(get_contract_repository),
    service: AgentExecutionService = Depends(get_agent_execution_service),
):

    extracted = _extract_message(payload)

    # Non-message events (status updates, etc.) are acknowledged and ignored.
    if extracted is None:
        return {"status": "ignored"}

    message_id, phone, body = extracted

    contract = contract_repository.get_by_whatsapp_chat_id(phone)

    # Unknown sender -> acknowledge so Meta stops retrying.
    if contract is None:
        return {"status": "unknown_contract"}

    try:
        service.execute(
            contract_id=contract.id,
            message_id=message_id,
            message=body,
        )
    except Exception:
        # Never surface a non-200 to Meta; just record it for diagnosis.
        logger.exception(
            "Agent execution failed for message %s",
            message_id,
        )

    return {"status": "ok"}
