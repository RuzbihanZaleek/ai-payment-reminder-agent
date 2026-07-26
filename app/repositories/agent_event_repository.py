from sqlalchemy.orm import Session

from app.models.agent_event import AgentEvent


class AgentEventRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, event: AgentEvent ) -> AgentEvent:
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        return event

    def get_by_id( self, event_id: int) -> AgentEvent | None:
        return (
            self.db.query(AgentEvent)
            .filter(AgentEvent.id == event_id)
            .first()
        )

    def get_by_run_id( self, agent_run_id: int) -> list[AgentEvent]:
        return (
            self.db.query(AgentEvent)
            .filter(AgentEvent.agent_run_id == agent_run_id)
            .all()
        )

    def update( self, event: AgentEvent ) -> AgentEvent:
        self.db.commit()
        self.db.refresh(event)

        return event
