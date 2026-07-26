from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun


class AgentRunRepository:

    def __init__( self, db: Session):
        self.db = db

    def create( self, agent_run: AgentRun ) -> AgentRun:
        self.db.add(agent_run)
        self.db.commit()
        self.db.refresh(agent_run)

        return agent_run

    def get_by_id( self, agent_run_id: int) -> AgentRun | None:
        return (
            self.db.query(AgentRun)
            .filter(AgentRun.id == agent_run_id)
            .first()
        )

    def get_all( self ) -> list[AgentRun]:
        return (
            self.db.query(AgentRun)
            .all()
        )

    def update( self, agent_run: AgentRun ) -> AgentRun:
        self.db.commit()
        self.db.refresh(agent_run)

        return agent_run
