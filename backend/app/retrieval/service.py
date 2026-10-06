import asyncio
import time
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ingestion.service import IngestionService
from backend.app.retrieval.hybrid_search import HybridSearchEngine, SearchResult
from backend.app.retrieval.reranker import FlashRankReranker


class TwoStageRetrievalService:
    """
    Orquestrador do Motor de Busca em 2 Etapas:
    Etapa 1: Busca Híbrida paralela (pgvector Cosine + PostgreSQL FTS) fundidas por RRF (Top-15)
    Etapa 2: Reranking local por Cross-Encoder FlashRank (Top-5)
    """

    def __init__(self):
        self.hybrid_engine = HybridSearchEngine(rrf_k=60)
        self.reranker = FlashRankReranker()
        self.ingestion_service = IngestionService()

    async def search(
        self,
        query: str,
        session: AsyncSession,
        top_candidates: int = 15,
        final_top_k: int = 5,
    ) -> List[SearchResult]:
        start_time = time.perf_counter()

        # 1. Gera embedding da pergunta
        query_vector = await self.ingestion_service.generate_query_embedding(query)

        # 2. Executa busca vetorial e léxica
        dense_results = await self.hybrid_engine.dense_search(
            query_vector=query_vector, session=session, top_k=20
        )
        sparse_results = await self.hybrid_engine.sparse_search(
            query_text=query, session=session, top_k=20
        )

        # 3. Fusão dos rankings via Reciprocal Rank Fusion (RRF)
        fused_candidates = self.hybrid_engine.reciprocal_rank_fusion(
            dense_results=dense_results,
            sparse_results=sparse_results,
            top_k=top_candidates,
        )

        if not fused_candidates:
            return []

        # 4. Etapa 2: Reranking com Cross-Encoder local (FlashRank)
        reranked_results = self.reranker.rerank(
            query=query,
            candidates=fused_candidates,
            top_k=final_top_k,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        # Metadados de latência registrados para observabilidade
        for res in reranked_results:
            res.metadata["retrieval_latency_ms"] = round(elapsed_ms, 2)

        return reranked_results
