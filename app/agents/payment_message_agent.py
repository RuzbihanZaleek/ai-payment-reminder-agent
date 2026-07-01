from app.schemas.payment_detection import (
    PaymentDetectionResult
)


class PaymentMessageAgent:

    def __init__( self, llm):
        self.llm = llm


    def analyze_message( self, message: str ) -> PaymentDetectionResult:

        response = self.llm.invoke(
            message
        )

        return PaymentDetectionResult.model_validate(
            response
        )