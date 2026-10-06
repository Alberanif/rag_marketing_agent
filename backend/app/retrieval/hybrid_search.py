from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import DocumentChunk


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section_title: Optional[str] = None
    content: str
    score: float
    rank_dense: Optional[int] = None
    rank_sparse: Optional[int] = None
    metadata: Dict[str, Any] = {}


class HybridSearchEngine:
    """
    Motor de Busca Híbrida combinando busca vetorial densa (pgvector Cosine Distance)
    e busca léxica esparsa (PostgreSQL Full-Text Search com ts_rank_cd), fundidas via
    Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    async def dense_search(
        self,
        query_vector: List[float],
        session: AsyncSession,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        Busca vetorial densa com pgvector utilizando operador de distância de cosseno (<=>).
        """
        # Em pgvector sqlalchemy, cosine_distance é suportado diretamente
        stmt = (
            select(
                DocumentChunk,
                DocumentChunk.embedding.cosine_distance(query_vector).label("distance"),
            )
            .where(DocumentChunk.embedding.isnot(None))
            .order_by("distance")
            .limit(top_k)
        )

        res = await session.execute(stmt)
        rows = res.all()

        results = []
        for rank, (chunk, distance) in enumerate(rows, start=1):
            # Converte distância cosseno (0 a 2) em similaridade (1 - distance)
            similarity = max(0.0, 1.0 - float(distance))
            doc_name = chunk.metadata_.get("document_name", "Desconhecido")
            results.append(
                SearchResult(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    document_name=doc_name,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    score=similarity,
                    rank_dense=rank,
                    metadata=chunk.metadata_,
                )
            )
        return results

    async def sparse_search(
        self,
        query_text: str,
        session: AsyncSession,
        top_k: int = 20,
    ) -> List[SearchResult]:
        """
        Busca léxica esparsa utilizando PostgreSQL Full Text Search com ranking por densidade (ts_rank_cd).
        """
        # websearch_to_tsquery suporta operadores comuns (aspas, or, etc.)
        ts_query = func.websearch_to_tsquery("portuguese", query_text)
        rank_expr = func.ts_rank_cd(DocumentChunk.tsv_content, ts_query).label("rank_score")

        stmt = (
            select(DocumentChunk, rank_expr)
            .where(DocumentChunk.tsv_content.op("@@")(ts_query))
            .order_by(desc("rank_score"))
            .limit(top_k)
        )

        res = await session.execute(stmt)
        rows = res.all()

        # Se websearch não retornar nada (ex: termos com pontuação ou abreviações não parseadas),
        # tenta plainto_tsquery como fallback léxico
        if not rows:
            ts_plain = func.plainto_tsquery("portuguese", query_text)
            rank_expr_plain = func.ts_rank_cd(DocumentChunk.tsv_content, ts_plain).label("rank_score")
            stmt = (
                select(DocumentChunk, rank_expr_plain)
                .where(DocumentChunk.tsv_content.op("@@")(ts_plain))
                .order_by(desc("rank_score"))
                .limit(top_k)
            )
            res = await session.execute(stmt)
            rows = res.all()

        results = []
        for rank, (chunk, rank_score) in enumerate(rows, start=1):
            doc_name = chunk.metadata_.get("document_name", "Desconhecido")
            results.append(
                SearchResult(
                    chunk_id=str(chunk.id),
                    document_id=str(chunk.document_id),
                    document_name=doc_name,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    score=float(rank_score),
                    rank_sparse=rank,
                    metadata=chunk.metadata_,
                )
            )
        return results

    def reciprocal_rank_fusion(
        self,
        dense_results: List[SearchResult],
        sparse_results: List[SearchResult],
        top_k: int = 15,
    ) -> List[SearchResult]:
        """
        Funde os resultados densos e esparsos utilizando Reciprocal Rank Fusion (RRF).
        RRF_Score(d) = sum(1 / (k + rank))
        """
        doc_scores: Dict[str, float] = {}
        doc_map: Dict[str, SearchResult] = {}

        # Pontua ranking denso
        for item in dense_results:
            rank = item.rank_dense or 999
            rrf_score = 1.0 / (self.rrf_k + rank)
            doc_scores[item.chunk_id] = doc_scores.get(item.chunk_id, 0.0) + rrf_score
            doc_map[item.chunk_id] = item

        # Pontua ranking esparso
        for item in sparse_results:
            rank = item.rank_sparse or 999
            rrf_score = 1.0 / (self.rrf_k + rank)
            doc_scores[item.chunk_id] = doc_scores.get(item.chunk_id, 0.0) + rrf_score
            if item.chunk_id in doc_map:
                doc_map[item.chunk_id].rank_sparse = item.rank_sparse
            else:
                doc_map[item.chunk_id] = item

        # Ordena por score final de RRF
        sorted_chunk_ids = sorted(
            doc_scores.keys(), key=lambda cid: doc_scores[cid], reverse=True
        )

        fused_results: List[SearchResult] = []
        for cid in sorted_chunk_ids[:top_k]:
            item = doc_map[cid]
            item.score = doc_scores[cid]
            fused_results.append(item)

        return fused_results
