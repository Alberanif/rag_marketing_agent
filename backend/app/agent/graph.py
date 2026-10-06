from typing import Any, Dict, Literal
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.agent.nodes import AgentNodes
from backend.app.agent.state import AgentState
from backend.app.schemas.chart import AgentResponse, ChartDataset, Citation


class LolaAgent:
    """
    Agente Autônomo Lola implementado em LangGraph com fluxo auto-reflexivo CRAG:
    Router -> Retrieve -> Grader -> [Rewrite -> Retrieve] -> Generate -> End
    """

    def __init__(self, nodes: AgentNodes):
        self.nodes = nodes
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # Adiciona os nós do grafo
        workflow.add_node("router", self.nodes.router_node)
        # O nó retrieve precisa de session injetada via closure/wrapper
        workflow.add_node("retrieve", self._retrieve_wrapper)
        workflow.add_node("grader", self.nodes.grader_node)
        workflow.add_node("rewrite_query", self.nodes.rewrite_query_node)
        workflow.add_node("generator", self.nodes.generator_node)

        # Define o ponto de entrada
        workflow.set_entry_point("router")

        # Transição condicional a partir do Router
        def route_decision(state: AgentState) -> Literal["retrieve", "end"]:
            if state.get("is_analytical", True):
                return "retrieve"
            return "end"

        workflow.add_conditional_edges(
            "router",
            route_decision,
            {
                "retrieve": "retrieve",
                "end": END,
            },
        )

        # Retrieve sempre segue para Grader
        workflow.add_edge("retrieve", "grader")

        # Transição condicional a partir do Grader
        def grader_decision(state: AgentState) -> Literal["generate", "rewrite"]:
            if state.get("doc_relevance") == "relevant":
                return "generate"
            if state.get("retry_count", 0) < 2:
                return "rewrite"
            return "generate"

        workflow.add_conditional_edges(
            "grader",
            grader_decision,
            {
                "generate": "generator",
                "rewrite": "rewrite_query",
            },
        )

        # Ciclo auto-reflexivo: Reescrita de query retorna ao Retriever
        workflow.add_edge("rewrite_query", "retrieve")

        # Generator finaliza o fluxo
        workflow.add_edge("generator", END)

        return workflow.compile()

    async def _retrieve_wrapper(self, state: AgentState) -> Dict[str, Any]:
        # A sessão é armazenada no contexto de execução do run
        session = getattr(self, "_active_session", None)
        return await self.nodes.retrieve_node(state, session)

    async def run(self, query: str, session: AsyncSession) -> AgentResponse:
        """
        Executa a inferência do grafo e devolve a resposta estruturada.
        """
        self._active_session = session

        initial_state: AgentState = {
            "messages": [],
            "query": query,
            "is_analytical": True,
            "retrieved_docs": [],
            "doc_relevance": "insufficient",
            "retry_count": 0,
            "rewritten_query": None,
            "answer": None,
            "citations": [],
            "chart_payload": None,
        }

        final_state = await self.graph.ainvoke(initial_state)

        # Converte para o schema tipado AgentResponse
        citations = [Citation(**c) for c in final_state.get("citations", [])]
        chart = None
        if final_state.get("chart_payload"):
            chart = ChartDataset(**final_state["chart_payload"])

        return AgentResponse(
            answer_markdown=final_state.get("answer", "Sem resposta gerada."),
            citations=citations,
            chart=chart,
        )
