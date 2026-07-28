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


logger = get_logger(__name__)

# Assistant conversations are keyed per user (there is no WhatsApp chat here).
_HISTORY_LIMIT = 10


class AssistantService:

    def __init__(
        self,
        conversation_memory_service,
        tool_executor: AssistantToolExecutor,
        llm,
        audit_service=None,
    ):
        self.conversation_memory_service = conversation_memory_service
        self.tool_executor = tool_executor
        self.llm = llm
        self.audit_service = audit_service

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

        start = time.perf_counter()

        intent_result = self.llm.detect_intent(message, history)
        intent = intent_result.intent

        logger.info("assistant_query", extra={"intent": intent.value})
        self._audit(user_id, "ASSISTANT_QUERY", conversation.id, {"intent": intent.value})

        gathered = self.tool_executor.gather(intent_result, user_id)

        response = self.llm.generate(
            ASSISTANT_SYSTEM_PROMPT,
            message,
            history,
            gathered["context"],
        )

        duration_ms = int((time.perf_counter() - start) * 1000)

        # Persist the turn (reuses the existing conversation memory service).
        self.conversation_memory_service.store_user_message(conversation.id, message)
        self.conversation_memory_service.store_assistant_message(
            conversation.id, response
        )

        # Observability: intent, duration, and which tools ran (never the content).
        tool_calls = gathered["tool_calls"]
        logger.info(
            "assistant_response",
            extra={
                "intent": intent.value,
                "duration_ms": duration_ms,
                "tool_calls": tool_calls,
            },
        )
        self._audit(
            user_id,
            "ASSISTANT_RESPONSE",
            conversation.id,
            {"intent": intent.value, "duration_ms": duration_ms, "tool_calls": tool_calls},
        )

        return {"message": response, "intent": intent.value}

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
