import pytest
from backend.app.retrieval.hybrid_search import HybridSearchEngine, SearchResult
from backend.app.retrieval.service import TwoStageRetrievalService
from backend.app.database import AsyncSessionLocal


def test_rrf_scoring_algorithm():
    engine = HybridSearchEngine(rrf_k=60)

    # Documento A: Rank 1 no Denso, Rank 2 no Esparso
    # Documento B: Rank 2 no Denso, Ausente no Esparso
    # Documento C: Ausente no Denso, Rank 1 no Esparso

    dense = [
        SearchResult(
            chunk_id="chunk-A",
            document_id="doc-1",
            document_name="doc.pdf",
            page_number=1,
            content="Conteudo A",
            score=0.9,
            rank_dense=1,
        ),
        SearchResult(
            chunk_id="chunk-B",
            document_id="doc-1",
            document_name="doc.pdf",
            page_number=1,
            content="Conteudo B",
            score=0.8,
            rank_dense=2,
        ),
    ]

    sparse = [
        SearchResult(
            chunk_id="chunk-C",
            document_id="doc-1",
            document_name="doc.pdf",
            page_number=1,
            content="Conteudo C",
            score=5.0,
            rank_sparse=1,
        ),
        SearchResult(
            chunk_id="chunk-A",
            document_id="doc-1",
            document_name="doc.pdf",
            page_number=1,
            content="Conteudo A",
            score=4.0,
            rank_sparse=2,
        ),
    ]

    fused = engine.reciprocal_rank_fusion(dense, sparse, top_k=3)

    assert len(fused) == 3
    # chunk-A deve ser o 1º colocado porque apareceu no topo de ambos:
    # Score A = 1/(60+1) + 1/(60+2) = 0.01639 + 0.01612 = 0.03251
    # Score C = 1/(60+1) = 0.01639
    # Score B = 1/(60+2) = 0.01612
    assert fused[0].chunk_id == "chunk-A"
    assert fused[1].chunk_id == "chunk-C"
    assert fused[2].chunk_id == "chunk-B"
    assert fused[0].score > fused[1].score > fused[2].score


@pytest.mark.asyncio
async def test_two_stage_retrieval_end_to_end():
    retrieval_service = TwoStageRetrievalService()

    async with AsyncSessionLocal() as session:
        # 1. Warm-up (já com modelo baixado em cache)
        await retrieval_service.search(
            query="warmup",
            session=session,
            top_candidates=5,
            final_top_k=2,
        )

        # 2. Busca real mensurada
        results = await retrieval_service.search(
            query="Qual foi o ROAS do Google Ads no relatório?",
            session=session,
            top_candidates=10,
            final_top_k=3,
        )

        assert isinstance(results, list)
        if len(results) > 0:
            top_hit = results[0]
            assert top_hit.content is not None
            assert top_hit.document_id is not None
            assert "retrieval_latency_ms" in top_hit.metadata
            # Critério de aceite: consulta híbrida em menos de 300ms
            assert top_hit.metadata["retrieval_latency_ms"] < 300
