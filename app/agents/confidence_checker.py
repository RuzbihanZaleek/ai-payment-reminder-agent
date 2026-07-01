from app.agents.state import AgentState


class ConfidenceChecker:

    MIN_CONFIDENCE = 0.80


    def check(self, state: AgentState) -> AgentState:

        detection = state.payment_detection

        if detection is None:
            state.requires_approval = True
            return state


        if detection.confidence < self.MIN_CONFIDENCE:
            state.requires_approval = True
        else:
            state.requires_approval = False


        return state