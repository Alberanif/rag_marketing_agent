from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ChartDataset(BaseModel):
    title: str = Field(description="Título do gráfico explicativo")
    chart_type: Literal["bar", "line", "area", "pie"] = Field(
        description="Tipo de visualização ideal para os dados"
    )
    x_axis_key: str = Field(
        description="Chave do eixo X, ex: 'mes', 'campanha', 'canal'"
    )
    data_keys: List[str] = Field(
        description="Lista de métricas numéricas a plotar, ex: ['roas', 'cac', 'investimento']"
    )
    series_labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="Rótulos amigáveis para a legenda, ex: {'roas': 'ROAS Médio'}",
    )
    data: List[Dict[str, Any]] = Field(
        description="Array de registros para os eixos do Recharts"
    )


class Citation(BaseModel):
    document_id: str = Field(description="ID do documento fonte")
    document_name: str = Field(description="Nome do arquivo fonte")
    page_number: int = Field(description="Número da página")
    section_title: Optional[str] = Field(default=None, description="Título da seção ou subtítulo")
    snippet: str = Field(description="Trecho citado do documento")


class AgentResponse(BaseModel):
    answer_markdown: str = Field(
        description="Resposta aprofundada, com insights e formatação markdown"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="Trechos, páginas e documentos utilizados como fonte",
    )
    chart: Optional[ChartDataset] = Field(
        default=None,
        description="Dados estruturados para renderização de gráfico no frontend",
    )
