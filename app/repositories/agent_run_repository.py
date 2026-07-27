from datetime import timedelta

from sqlalchemy.orm import Session

from app.models.agent_run import AgentRun
from app.repositories.filters import AgentRunFilter
from app.repositories.pagination import PageResult, apply_ordering, paginate
from app.enums.sort_order import SortOrder


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

    def get_for_user_page(
        self,
        user_id: int,
        run_filter: AgentRunFilter,
        page: int,
        page_size: int,
        order: SortOrder,
    ) -> PageResult:
        query = self._for_user_query(user_id)

        if run_filter.status is not None:
            query = query.filter(AgentRun.status == run_filter.status)

        if run_filter.date_from is not None:
            query = query.filter(AgentRun.created_at >= run_filter.date_from)

        if run_filter.date_to is not None:
            # created_at is a timestamp; add a day so the upper bound is an
            # inclusive whole-day boundary.
            query = query.filter(
                AgentRun.created_at < run_filter.date_to + timedelta(days=1)
            )

        query = apply_ordering(query, AgentRun.id, order)

        return paginate(query, page, page_size)

    def get_all( self ) -> list[AgentRun]:
        return (
            self.db.query(AgentRun)
            .all()
        )

    def update( self, agent_run: AgentRun ) -> AgentRun:
        self.db.commit()
        self.db.refresh(agent_run)

        return agent_run
