from pydantic import BaseModel, Field


class AssistantChatRequest(BaseModel):

    message: str = Field(min_length=1, max_length=2000)


class AssistantChatResponse(BaseModel):

    message: str
    intent: str
