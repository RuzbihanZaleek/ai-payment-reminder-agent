import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.db.session import SessionLocal
from app.container import (
    create_conversation_memory_service,
    create_message_router,
    create_assistant_service,
    create_whatsapp_notification_service,
    create_whatsapp_authorization_service,
)
from app.repositories.contract_repository import ContractRepository
from app.repositories.processed_message_repository import ProcessedMessageRepository
from app.services.agent_execution_service import AgentExecutionService
from app.services.conversation_memory_service import ConversationMemoryService
from app.core.rate_limit import rate_limit_webhook
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


def get_message_router():

    return create_message_router()


def get_assistant_service():

    db = SessionLocal()

    try:
        yield create_assistant_service(db=db)
    finally:
        db.close()


def get_whatsapp_notification_service():

    return create_whatsapp_notification_service()


def get_whatsapp_authorization_service():

    db = SessionLocal()

    try:
        yield create_whatsapp_authorization_service(db=db)
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


# Both paths map to the same handler so Meta can point at either the short
# `/webhook` or the conventional `/webhooks/whatsapp`. One implementation.
@router.get("/webhook")
@router.get("/webhooks/whatsapp")
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


@router.post("/webhook", dependencies=[Depends(rate_limit_webhook)])
@router.post("/webhooks/whatsapp", dependencies=[Depends(rate_limit_webhook)])
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
    message_router=Depends(get_message_router),
    assistant_service=Depends(get_assistant_service),
    notification_service=Depends(get_whatsapp_notification_service),
    whatsapp_authorization_service=Depends(get_whatsapp_authorization_service),
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

    # Tenant isolation: a phone number could match contracts owned by different
    # users. Resolve the owning user from the first matching contract, then scope
    # the candidate pool to that user so a single run never mixes tenants.
    owner_user_id = contracts[0].user_id
    contracts = [c for c in contracts if c.user_id == owner_user_id]

    # Lightweight candidate pool for the ContractResolverNode to select from.
    resolved_contracts = [_contract_summary(contract) for contract in contracts]

    # A primary contract is recorded on the AgentRun; the resolver node refines
    # which contract the payment actually applies to based on the message.
    primary_contract_id = contracts[0].id

    # Conversation memory: load prior context (summary + recent messages)
    # before running the agent. The current message is only persisted on
    # success, so a failed run leaves no conversation messages behind. The AI
    # assistant shares this same phone-keyed conversation.
    conversation = conversation_memory_service.get_or_create_conversation(phone)
    history = conversation_memory_service.get_history(conversation.id)

    try:
        # Route on the EXISTING payment detector: payments -> the unchanged
        # payment workflow; everything else -> the AI assistant.
        if message_router.is_payment(body, history["messages"]):
            _run_payment_workflow(
                service,
                conversation_memory_service,
                conversation,
                message_id,
                body,
                primary_contract_id,
                history,
                resolved_contracts,
            )
        else:
            _run_assistant(
                assistant_service,
                notification_service,
                whatsapp_authorization_service,
                owner_user_id,
                phone,
                body,
            )
    except Exception:
        # Never surface a non-200 to Meta; just record it for diagnosis.
        # A failed run is NOT marked processed, so Meta's retry can reprocess it.
        logger.exception("whatsapp_message_processing_failed message_id=%s", message_id)
        return {"status": "error"}

    # Only mark processed after a successful run.
    processed_message_repository.create(message_id=message_id, source="whatsapp")

    return {"status": "ok"}


def _run_payment_workflow(
    service,
    conversation_memory_service,
    conversation,
    message_id,
    body,
    primary_contract_id,
    history,
    resolved_contracts,
) -> None:
    """The original payment path (UNCHANGED behaviour)."""

    result = service.execute(
        contract_id=primary_contract_id,
        message_id=message_id,
        message=body,
        conversation_id=conversation.id,
        conversation_history=history["messages"],
        resolved_contracts=resolved_contracts,
    )

    conversation_memory_service.store_user_message(conversation.id, body)

    if result is not None and result.generated_message is not None:
        conversation_memory_service.store_assistant_message(
            conversation.id, result.generated_message
        )


def _run_assistant(
    assistant_service,
    notification_service,
    whatsapp_authorization_service,
    owner_user_id,
    phone,
    body,
) -> None:
    """Non-payment path: the AI assistant, scoped to the owning user.

    A WhatsApp authorization guard is supplied so lender-side WRITE actions are
    rejected on this channel (reads/payments are unaffected). The assistant
    persists the turn itself; the webhook only delivers the reply over WhatsApp.
    """

    def authorize(intent):
        return whatsapp_authorization_service.authorize(phone, intent)

    result = assistant_service.chat(
        owner_user_id, body, conversation_key=phone, action_authorizer=authorize
    )
    notification_service.send(phone, result["message"])
