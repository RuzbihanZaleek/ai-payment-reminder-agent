"""AI financial assistant service.

Orchestrates: load conversation history -> detect intent -> select & run
read-only tools -> generate a grounded natural-language answer -> persist the
turn. It is strictly READ-ONLY: it only ever reads through the tools; it never
creates payments, modifies contracts, sends reminders, or approves anything.
"""

import time

from app.core.logger import get_logger
from app.ai.prompts import ASSISTANT_SYSTEM_PROMPT
from app.ai.assistant.intent import AssistantIntent
from app.ai.assistant.tools import AssistantToolExecutor
from app.ai.actions.pending_action import ActionType


logger = get_logger(__name__)

# Assistant conversations are keyed per user (there is no WhatsApp chat here).
_HISTORY_LIMIT = 10

# Robust one-word confirmations handled deterministically (no LLM needed).
_CONFIRM_WORDS = {"yes", "y", "ok", "okay", "confirm", "proceed", "sure", "yep", "yeah"}
_CANCEL_WORDS = {"no", "n", "cancel", "stop", "nope", "abort", "never mind", "nevermind"}

# Write intents that must go through the confirm-first flow.
_WRITE_INTENTS = {
    AssistantIntent.CREATE_CONTRACT: ActionType.CREATE_CONTRACT,
    AssistantIntent.APPROVE_PAYMENT: ActionType.APPROVE_PAYMENT,
    AssistantIntent.REJECT_PAYMENT: ActionType.REJECT_PAYMENT,
    AssistantIntent.SEND_REMINDERS: ActionType.SEND_REMINDERS,
}
_UNSUPPORTED_INTENTS = {
    AssistantIntent.UPDATE_CONTRACT,
    AssistantIntent.DELETE_CONTRACT,
}


class AssistantService:

    def __init__(
        self,
        conversation_memory_service,
        tool_executor: AssistantToolExecutor,
        llm,
        audit_service=None,
        financial_memory_service=None,
        memory_extraction_service=None,
        action_service=None,
    ):
        self.conversation_memory_service = conversation_memory_service
        self.tool_executor = tool_executor
        self.llm = llm
        self.audit_service = audit_service
        self.financial_memory_service = financial_memory_service
        self.memory_extraction_service = memory_extraction_service
        self.action_service = action_service

    @staticmethod
    def _conversation_key(user_id: int) -> str:
        return f"assistant:user:{user_id}"

    def chat(self, user_id: int, message: str) -> dict:
        conversation = self.conversation_memory_service.get_or_create_conversation(
            self._conversation_key(user_id)
        )

        # History is loaded BEFORE the current turn is stored.
        history = self.conversation_memory_service.get_recent_history(
            conversation.id, limit=_HISTORY_LIMIT
        )

        # Relevant long-term financial memories (user-scoped -- never another
        # user's memories).
        memories = self._load_memories(user_id)

        start = time.perf_counter()
        tool_calls: list = []

        # 1. Deterministic YES/NO on a pending action (robust; no LLM call).
        shortcut = self._confirmation_shortcut(user_id, message)
        if shortcut is not None:
            response, intent_value = shortcut
        else:
            intent_result = self.llm.detect_intent(message, history)
            intent = intent_result.intent
            intent_value = intent.value

            if self.action_service is not None and intent in _WRITE_INTENTS:
                # WRITE: propose only -- never execute now.
                response = self._propose_action(user_id, intent, intent_result)
            elif self.action_service is not None and intent == AssistantIntent.CONFIRM_ACTION:
                response = self.action_service.confirm_and_execute(user_id)["message"]
            elif self.action_service is not None and intent == AssistantIntent.CANCEL_ACTION:
                response = self.action_service.cancel_latest(user_id)["message"]
            elif intent in _UNSUPPORTED_INTENTS:
                response = "Editing or deleting contracts isn't supported in this version."
            else:
                # READ: gather grounded data and let the LLM phrase the answer.
                gathered = self.tool_executor.gather(intent_result, user_id)
                tool_calls = gathered["tool_calls"]
                context = {**gathered["context"], "financial_memories": memories}
                response = self.llm.generate(
                    ASSISTANT_SYSTEM_PROMPT, message, history, context
                )

        duration_ms = int((time.perf_counter() - start) * 1000)

        logger.info("assistant_query", extra={"intent": intent_value})
        self._audit(user_id, "ASSISTANT_QUERY", conversation.id, {"intent": intent_value})

        # Persist the turn (reuses the existing conversation memory service).
        self.conversation_memory_service.store_user_message(conversation.id, message)
        self.conversation_memory_service.store_assistant_message(
            conversation.id, response
        )

        # Extract any long-term memory worth keeping (preferences/patterns).
        self._extract_memories(user_id, message, response)

        logger.info(
            "assistant_response",
            extra={
                "intent": intent_value,
                "duration_ms": duration_ms,
                "tool_calls": tool_calls,
            },
        )
        self._audit(
            user_id,
            "ASSISTANT_RESPONSE",
            conversation.id,
            {"intent": intent_value, "duration_ms": duration_ms, "tool_calls": tool_calls},
        )

        return {"message": response, "intent": intent_value}

    def _confirmation_shortcut(self, user_id: int, message: str):
        """Handle a bare YES/NO reply against a pending action, or return None."""

        if self.action_service is None:
            return None

        normalized = message.strip().lower()

        if normalized in _CONFIRM_WORDS:
            if self.action_service.get_latest_pending(user_id) is not None:
                result = self.action_service.confirm_and_execute(user_id)
                return result["message"], AssistantIntent.CONFIRM_ACTION.value
        elif normalized in _CANCEL_WORDS:
            if self.action_service.get_latest_pending(user_id) is not None:
                result = self.action_service.cancel_latest(user_id)
                return result["message"], AssistantIntent.CANCEL_ACTION.value

        return None

    def _propose_action(self, user_id: int, intent, intent_result) -> str:
        action_type = _WRITE_INTENTS[intent]

        if action_type == ActionType.CREATE_CONTRACT:
            params = {
                "name": intent_result.person,
                "total_amount": intent_result.amount,
                "daily_amount": intent_result.daily_amount,
            }
        elif action_type in (ActionType.APPROVE_PAYMENT, ActionType.REJECT_PAYMENT):
            params = {"payment_id": intent_result.payment_id}
        else:
            params = {}

        return self.action_service.propose(user_id, action_type, params)["message"]

    def _load_memories(self, user_id: int) -> list:
        if self.financial_memory_service is None:
            return []
        return self.financial_memory_service.get_relevant_memories(user_id)

    def _extract_memories(self, user_id: int, message: str, response: str) -> None:
        if self.memory_extraction_service is None:
            return
        # Memory extraction must never break the chat response.
        try:
            self.memory_extraction_service.extract(user_id, message, response)
        except Exception:
            logger.exception("memory_extraction_failed", extra={"user_id": user_id})

    def _audit(self, user_id: int, action: str, conversation_id: int, metadata: dict) -> None:
        if self.audit_service is None:
            return

        self.audit_service.record(
            action=getattr(self.audit_service, action),
            user_id=user_id,
            entity_type="conversation",
            entity_id=conversation_id,
            metadata=metadata,
        )
