from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.llm.prompts import PAYMENT_EXTRACTION_SYSTEM_PROMPT
from app.schemas.payment_detection import PaymentDetectionResult

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
        
        return self.chain.invoke({
            "message": message
        })