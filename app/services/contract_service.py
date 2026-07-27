from app.models.contract import Contract, ContractStatus
from app.schemas.contract import ContractCreate
from app.repositories.contract_repository import ContractRepository


class ContractService:

    def __init__(
        self,
        repository: ContractRepository
    ):
        self.repository = repository


    def create_contract(
        self,
        contract_data: ContractCreate,
        user_id: int | None = None
    ) -> Contract:

        contract = Contract(
            user_id=user_id,
            reference_code=contract_data.reference_code,
            name=contract_data.name,
            description=contract_data.description,
            total_amount=contract_data.total_amount,
            daily_amount=contract_data.daily_amount,
            currency=contract_data.currency.value,
            start_date=contract_data.start_date,
            end_date=contract_data.end_date,
            whatsapp_chat_id=contract_data.whatsapp_chat_id,
        )

        return self.repository.create(contract)


    def get_contract(
        self,
        contract_id: int
    ) -> Contract | None:

        return self.repository.get_by_id(contract_id)


    def get_all_contracts(
        self
    ) -> list[Contract]:

        return self.repository.get_all()


    def get_user_contracts(
        self,
        user_id: int,
        status: ContractStatus | None = None,
    ) -> list[Contract]:

        return self.repository.get_all_for_user(user_id, status)


    def delete_contract(
        self,
        contract_id: int
    ) -> bool:

        contract = self.repository.get_by_id(contract_id)

        if contract is None:
            return False

        self.repository.delete(contract)

        return True