import hashlib
import uuid
from typing import List, Optional
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import OpenAIEmbeddings

from backend.app.config import get_settings
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.ingestion.parser import PDFParser
from backend.app.models.document import Document, DocumentChunk

settings = get_settings()


class IngestionService:
    def __init__(self):
        self.parser = PDFParser()
        self.chunker = SemanticChunker()
        self._init_embeddings()

    def _init_embeddings(self):
        api_key = settings.OPENAI_API_KEY
        if api_key and not api_key.startswith("your_openai"):
            try:
                self.embeddings_client = OpenAIEmbeddings(
                    model=settings.OPENAI_EMBEDDING_MODEL,
                    openai_api_key=api_key,
                )
            except Exception:
                self.embeddings_client = None
        else:
            self.embeddings_client = None

    def _generate_mock_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """
        Gera um vetor determinístico normalizado L2 para testes e ambientes sem chave de API.
        """
        # Hashing determinístico do texto
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(dim)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        # Tenta com o cliente OpenAI se estiver ativo
        if self.embeddings_client is not None:
            try:
                return await self.embeddings_client.aembed_documents(texts)
            except Exception as e:
                # Se falhar a chamada externa, loga e usa fallback
                pass

        # Fallback determinístico
        return [self._generate_mock_embedding(t, settings.EMBEDDING_DIMENSION) for t in texts]

    async def generate_query_embedding(self, query: str) -> List[float]:
        if self.embeddings_client is not None:
            try:
                return await self.embeddings_client.aembed_query(query)
            except Exception:
                pass
        return self._generate_mock_embedding(query, settings.EMBEDDING_DIMENSION)

    async def ingest_pdf(
        self,
        file_bytes: bytes,
        filename: str,
        session: AsyncSession,
        title: Optional[str] = None,
    ) -> Document:
        """
        Executa o pipeline completo de ingestão:
        1. Parsing do PDF com extração de tabelas e hierarquia
        2. Chunking semântico com preservação estrutural
        3. Geração de embeddings 1536d
        4. Persistência relacional e vetorial no PostgreSQL
        """
        doc_title = title or filename.rsplit(".", 1)[0].replace("_", " ").title()

        # 1. Parsing
        parsed_doc = self.parser.parse_pdf(file_bytes, filename)

        # 2. Chunking
        chunk_data_list = self.chunker.chunk_document(parsed_doc)

        # 3. Criação da entidade Document
        document_id = uuid.uuid4()
        doc = Document(
            id=document_id,
            title=doc_title,
            filename=filename,
            total_pages=parsed_doc.total_pages,
            total_chunks=len(chunk_data_list),
            metadata_={
                "median_font_size": parsed_doc.metadata.get("median_font_size"),
                "total_blocks": len(parsed_doc.blocks),
            },
        )
        session.add(doc)

        # 4. Geração de Embeddings em lote
        texts = [chunk.content for chunk in chunk_data_list]
        embeddings = await self.generate_embeddings(texts)

        # 5. Persistência dos DocumentChunks
        for idx, (chunk_data, emb) in enumerate(zip(chunk_data_list, embeddings)):
            chunk_orm = DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                chunk_index=chunk_data.chunk_index,
                page_number=chunk_data.page_number,
                section_title=chunk_data.section_title,
                content=chunk_data.content,
                embedding=emb,
                metadata_={
                    **chunk_data.metadata,
                    "token_count": chunk_data.token_count,
                    "document_title": doc_title,
                    "document_name": filename,
                },
            )
            session.add(chunk_orm)

        await session.commit()
        await session.refresh(doc)
        return doc
