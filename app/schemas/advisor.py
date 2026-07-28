from pydantic import BaseModel


class AdvisorResponse(BaseModel):

    summary: str
    risks: list[str]
    recommendations: list[str]
