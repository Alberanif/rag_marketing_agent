from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.graph import LolaAgent
from backend.app.agent.nodes import AgentNodes
from backend.app.database import get_db
from backend.app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat & Lola Agent"])

# Singleton do agente Lola
_agent_instance: LolaAgent = None


def get_agent() -> LolaAgent:
    global _agent_instance
    if _agent_instance is None:
        nodes = AgentNodes()
        _agent_instance = LolaAgent(nodes)
    return _agent_instance


@router.post(
    "",
    response_model=ChatResponse,
    summary="Interact with Lola Agent (Q&A with grounded citations and dynamic Recharts payload)",
)
async def chat_with_agent(
    request: ChatRequest,
    session: AsyncSession = Depends(get_db),
    agent: LolaAgent = Depends(get_agent),
):
    try:
        response = await agent.run(query=request.query, session=session)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar mensagem com a Lola: {str(e)}",
        )
