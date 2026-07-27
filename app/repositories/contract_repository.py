from sqlalchemy.orm import Session

from app.models.contract import Contract, ContractStatus


class ContractRepository:

    def __init__(self, db: Session):
        self.db = db


    def create(
        self,
        contract: Contract
    ) -> Contract:

        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)

        return contract


    def get_by_id(
        self,
        contract_id: int
    ) -> Contract | None:

        return (
            self.db.query(Contract)
            .filter(
                Contract.id == contract_id
            )
            .first()
        )


    def get_all(self) -> list[Contract]:

        return (
            self.db.query(Contract)
            .all()
        )


    def get_active_by_whatsapp_chat_id(
        self,
        whatsapp_chat_id: str
    ) -> list[Contract]:

        return (
            self.db.query(Contract)
            .filter(
                Contract.whatsapp_chat_id == whatsapp_chat_id
            )
            .filter(
                Contract.status == ContractStatus.ACTIVE
            )
            .all()
        )


    def get_by_whatsapp_chat_id(
        self,
        whatsapp_chat_id: str
    ) -> Contract | None:

        return (
            self.db.query(Contract)
            .filter(
                Contract.whatsapp_chat_id == whatsapp_chat_id
            )
            .first()
        )


    def delete(
        self,
        contract: Contract
    ) -> None:

        self.db.delete(contract)
        self.db.commit()