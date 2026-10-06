import pytest
from backend.app.agent.nodes import AgentNodes
from backend.app.agent.graph import LolaAgent
from backend.app.database import AsyncSessionLocal
from backend.app.schemas.chart import AgentResponse


@pytest.mark.asyncio
async def test_agent_casual_greeting_routes_directly():
    nodes = AgentNodes()
    agent = LolaAgent(nodes)

    async with AsyncSessionLocal() as session:
        response = await agent.run(query="Olá, quem é você?", session=session)

        assert isinstance(response, AgentResponse)
        assert "Lola" in response.answer_markdown
        assert response.chart is None
        assert len(response.citations) == 0


@pytest.mark.asyncio
async def test_agent_analytical_query_runs_crag_and_returns_chart():
    nodes = AgentNodes()
    agent = LolaAgent(nodes)

    async with AsyncSessionLocal() as session:
        response = await agent.run(
            query="Qual foi o investimento e o ROAS dos canais de mídia no relatório?",
            session=session,
        )

        assert isinstance(response, AgentResponse)
        assert len(response.answer_markdown) > 0
        # Citações extraídas dos documentos recuperados
        assert len(response.citations) > 0
        assert response.citations[0].document_name is not None

        # Deve gerar o payload de dados de gráfico para o Recharts
        if response.chart is not None:
            chart = response.chart
            assert chart.title is not None
            assert chart.chart_type in ["bar", "line", "area", "pie"]
            assert chart.x_axis_key is not None
            assert len(chart.data) > 0
