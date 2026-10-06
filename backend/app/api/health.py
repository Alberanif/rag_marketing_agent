from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.document import Document, DocumentChunk

router = APIRouter(tags=["Health & Stats"])


@router.get("/health", summary="Service health and database status check")
async def health_check(session: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    pgvector_status = "active"
    total_docs = 0
    total_chunks = 0

    try:
        # Testa conexão e extensão pgvector
        await session.execute(text("SELECT 1;"))
        res = await session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        )
        version_row = res.scalar_one_or_none()
        if not version_row:
            pgvector_status = "not_found"

        # Estatísticas
        doc_count_res = await session.execute(select(func.count(Document.id)))
        total_docs = doc_count_res.scalar() or 0

        chunk_count_res = await session.execute(select(func.count(DocumentChunk.id)))
        total_chunks = chunk_count_res.scalar() or 0
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        pgvector_status = "error"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "pgvector": pgvector_status,
        "total_documents": total_docs,
        "total_chunks": total_chunks,
    }
