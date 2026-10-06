from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langgraph.graph.message import add_messages


class RetrievedDoc(TypedDict):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section_title: Optional[str]
    content: str
    score: float
    metadata: Dict[str, Any]


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    query: str
    is_analytical: bool
    retrieved_docs: List[RetrievedDoc]
    doc_relevance: str  # "relevant" | "insufficient"
    retry_count: int
    rewritten_query: Optional[str]
    answer: Optional[str]
    citations: List[Dict[str, Any]]
    chart_payload: Optional[Dict[str, Any]]
