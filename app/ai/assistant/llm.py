"""LLM boundary for the assistant.

Two responsibilities, both injectable so tests can substitute a fake with no API
key:

- ``detect_intent(message, history) -> IntentDetectionResult``
- ``generate(system_prompt, message, history, context) -> str``

The real implementation uses ChatOpenAI (structured output for intent, plain
text for the answer) and is imported lazily so importing this module never
requires langchain/an API key.
"""

import json

from app.core.config import settings
from app.core.logger import get_logger
from app.ai.assistant.intent import IntentDetectionResult
from app.ai.assistant.prompts import INTENT_DETECTION_PROMPT


logger = get_logger(__name__)


class OpenAIAssistantLLM:

    def __init__(self):
        # Imported lazily so tests injecting a fake llm don't pull in langchain.
        from langchain_openai import ChatOpenAI

        self._chat = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )

    @staticmethod
    def _to_langchain_history(history):
        from langchain_core.messages import AIMessage, HumanMessage

        messages = []
        for item in history or []:
            role = item.get("role")
            content = item.get("content", "")
            if role == "ASSISTANT":
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return messages

    def detect_intent(self, message: str, history: list | None = None) -> IntentDetectionResult:
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", INTENT_DETECTION_PROMPT),
                MessagesPlaceholder("history", optional=True),
                ("human", "{message}"),
            ]
        )
        chain = prompt | self._chat.with_structured_output(IntentDetectionResult)

        return chain.invoke(
            {"message": message, "history": self._to_langchain_history(history)}
        )

    def generate(
        self,
        system_prompt: str,
        message: str,
        history: list | None,
        context: dict,
    ) -> str:
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("history", optional=True),
                (
                    "human",
                    "Application data (JSON, already scoped to me):\n{context}\n\n"
                    "My question: {message}",
                ),
            ]
        )
        chain = prompt | self._chat

        result = chain.invoke(
            {
                "message": message,
                "context": json.dumps(context, default=str),
                "history": self._to_langchain_history(history),
            }
        )

        return getattr(result, "content", str(result))
