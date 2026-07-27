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

    def get_recent( self, limit: int = 20 ) -> list[AgentRun]:
        return (
            self.db.query(AgentRun)
            .order_by(AgentRun.id.desc())
            .limit(limit)
            .all()
        )

    def _for_user_query( self, user_id: int ):
        from app.models.contract import Contract

        return (
            self.db.query(AgentRun)
            .join(Contract, AgentRun.contract_id == Contract.id)
            .filter(Contract.user_id == user_id)
        )

    def get_all_for_user( self, user_id: int ) -> list[AgentRun]:
        return self._for_user_query(user_id).all()

    def get_recent_for_user( self, user_id: int, limit: int = 20 ) -> list[AgentRun]:
        return (
            self._for_user_query(user_id)
            .order_by(AgentRun.id.desc())
            .limit(limit)
            .all()
        )

    def get_by_id_for_user( self, agent_run_id: int, user_id: int ) -> AgentRun | None:
        return (
            self._for_user_query(user_id)
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
