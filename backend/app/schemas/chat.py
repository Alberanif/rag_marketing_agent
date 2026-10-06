from pydantic import BaseModel, Field

from backend.app.schemas.chart import AgentResponse


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Pergunta ou instrução para a agente Lola")


class ChatResponse(AgentResponse):
    pass
