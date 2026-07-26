from app.agents.state import AgentState
from app.agents.confidence_checker import ConfidenceChecker


class ConfidenceCheckerNode:

    def __init__(
        self,
        confidence_checker: ConfidenceChecker,
    ):
        self.confidence_checker = confidence_checker

    def execute(
        self,
        state: AgentState,
    ) -> AgentState:

        return self.confidence_checker.check(state)
