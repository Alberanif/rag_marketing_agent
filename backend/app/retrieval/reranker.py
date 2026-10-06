from typing import List, Optional
from flashrank import Ranker, RerankRequest

from backend.app.config import get_settings
from backend.app.retrieval.hybrid_search import SearchResult

settings = get_settings()


class FlashRankReranker:
    """
    Reranker de Cross-Encoder local utilizando FlashRank (ms-marco-TinyBERT-L-2-v2).
    Executa localmente em CPU com altíssima velocidade e zero custo de API.
    """

    _ranker_instance: Optional[Ranker] = None

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.RERANKER_MODEL_NAME

    @classmethod
    def _get_ranker(cls, model_name: str) -> Ranker:
        if cls._ranker_instance is None:
            # Inicializa Ranker com o modelo cross-encoder leve
            cls._ranker_instance = Ranker(model_name=model_name)
        return cls._ranker_instance

    def rerank(
        self,
        query: str,
        candidates: List[SearchResult],
        top_k: int = 5,
    ) -> List[SearchResult]:
        if not candidates:
            return []

        try:
            ranker = self._get_ranker(self.model_name)
            passages = [
                {
                    "id": c.chunk_id,
                    "text": f"{c.section_title or ''}\n{c.content}",
                    "meta": {
                        "document_id": c.document_id,
                        "document_name": c.document_name,
                        "page_number": c.page_number,
                    },
                }
                for c in candidates
            ]

            request = RerankRequest(query=query, passages=passages)
            ranked_results = ranker.rerank(request)

            candidate_lookup = {c.chunk_id: c for c in candidates}
            final_results: List[SearchResult] = []

            for item in ranked_results[:top_k]:
                chunk_id = item["id"]
                original = candidate_lookup.get(chunk_id)
                if original:
                    # Atualiza o score com a pontuação de relevância do Cross-Encoder
                    original.score = float(item.get("score", original.score))
                    final_results.append(original)

            return final_results
        except Exception:
            # Fallback seguro caso haja erro no runtime do FlashRank
            return candidates[:top_k]
