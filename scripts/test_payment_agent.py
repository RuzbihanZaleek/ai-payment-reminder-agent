from app.agents.payment_message_agent import PaymentMessageAgent
from app.llm.client import OpenAIClient


def main():

    agent = PaymentMessageAgent(
        OpenAIClient()
    )

    result = agent.analyze_message(
        "Bro I transferred 250 today"
    )

    print(result)


if __name__ == "__main__":
    main()