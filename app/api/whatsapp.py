import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.db.session import SessionLocal
from app.container import create_conversation_memory_service
from app.repositories.contract_repository import ContractRepository
from app.repositories.processed_message_repository import ProcessedMessageRepository
from app.services.agent_execution_service import AgentExecutionService
from app.services.conversation_memory_service import ConversationMemoryService
from app.api.agent import get_agent_execution_service


logger = logging.getLogger(__name__)

router = APIRouter(tags=["whatsapp"])


def get_contract_repository():

    db = SessionLocal()

    try:
        yield ContractRepository(db)
    finally:
        db.close()


def get_processed_message_repository():

    db = SessionLocal()

    try:
        yield ProcessedMessageRepository(db)
    finally:
        db.close()


def get_conversation_memory_service():

    db = SessionLocal()

    try:
        yield create_conversation_memory_service(db=db)
    finally:
        db.close()


def _contract_summary(contract) -> dict:
    """Lightweight representation of a contract for the resolver node."""

    return {
        "id": contract.id,
        "reference_code": contract.reference_code,
        "total_amount": contract.total_amount,
        "daily_amount": contract.daily_amount,
        "whatsapp_chat_id": contract.whatsapp_chat_id,
    }


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
    processed_message_repository: ProcessedMessageRepository = Depends(
        get_processed_message_repository
    ),
    conversation_memory_service: ConversationMemoryService = Depends(
        get_conversation_memory_service
    ),
    service: AgentExecutionService = Depends(get_agent_execution_service),
):

    extracted = _extract_message(payload)

    # Non-message events (status updates, etc.) are acknowledged and ignored.
    if extracted is None:
        return {"status": "ignored"}

    message_id, phone, body = extracted

    # Idempotency: a message we've already processed is acknowledged and dropped
    # without re-running the workflow.
    if processed_message_repository.exists(message_id):
        return {"status": "duplicate"}

    contracts = contract_repository.get_active_by_whatsapp_chat_id(phone)

    # Unknown sender (no active contracts) -> acknowledge so Meta stops retrying.
    if not contracts:
        return {"status": "unknown_contract"}

    # Lightweight candidate pool for the ContractResolverNode to select from.
    resolved_contracts = [_contract_summary(contract) for contract in contracts]

    # A primary contract is recorded on the AgentRun; the resolver node refines
    # which contract the payment actually applies to based on the message.
    primary_contract_id = contracts[0].id

    # Conversation memory: load prior context (summary + recent messages)
    # before running the agent. The current message is only persisted on
    # success, so a failed run leaves no conversation messages behind.
    conversation = conversation_memory_service.get_or_create_conversation(phone)
    history = conversation_memory_service.get_history(conversation.id)

    try:
        result = service.execute(
            contract_id=primary_contract_id,
            message_id=message_id,
            message=body,
            conversation_id=conversation.id,
            conversation_history=history["messages"],
            resolved_contracts=resolved_contracts,
        )
    except Exception:
        # Never surface a non-200 to Meta; just record it for diagnosis.
        # A failed run is NOT marked processed, so Meta's retry can reprocess it.
        logger.exception(
            "Agent execution failed for message %s",
            message_id,
        )
        return {"status": "error"}

    # Only after a successful run: persist the user message and assistant reply.
    conversation_memory_service.store_user_message(conversation.id, body)

    if result is not None and result.generated_message is not None:
        conversation_memory_service.store_assistant_message(
            conversation.id,
            result.generated_message,
        )

    # Only mark processed after a successful run.
    processed_message_repository.create(
        message_id=message_id,
        source="whatsapp",
    )

    return {"status": "ok"}
