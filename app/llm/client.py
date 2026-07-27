import time

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.logger import get_logger
from app.llm.prompts import PAYMENT_EXTRACTION_SYSTEM_PROMPT
from app.schemas.payment_detection import PaymentDetectionResult


logger = get_logger(__name__)

class OpenAIClient:
    
    def __init__(self):
        self.llm = ChatOpenAI(model = settings.OPENAI_MODEL, api_key = settings.OPENAI_API_KEY, temperature = 0)
        
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", PAYMENT_EXTRACTION_SYSTEM_PROMPT),
                ("human", "{message}")
            ]
        )
        
        self.chain = (self.prompt | self.llm.with_structured_output(PaymentDetectionResult))
        
    def invoke(self, message: str) -> PaymentDetectionResult:

        logger.info(
            "openai_request_started",
            extra={"model": settings.OPENAI_MODEL},
        )

        start = time.perf_counter()

        try:
            result = self.chain.invoke({
                "message": message
            })
        except Exception as exc:
            logger.error(
                "openai_request_failed",
                extra={
                    "model": settings.OPENAI_MODEL,
                    "duration_ms": int((time.perf_counter() - start) * 1000),
                    "error": str(exc),
                },
            )
            raise

        logger.info(
            "openai_request_completed",
            extra={
                "model": settings.OPENAI_MODEL,
                "duration_ms": int((time.perf_counter() - start) * 1000),
            },
        )

        return result