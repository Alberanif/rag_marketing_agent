import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.ingestion.service import IngestionService
from backend.app.models.document import Document, DocumentChunk
from backend.app.schemas.document import (
    DocumentChunkResponse,
    DocumentListResponse,
    DocumentResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])
ingestion_service = IngestionService()


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a marketing PDF document",
)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas arquivos no formato PDF são suportados.",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O arquivo enviado está vazio.",
        )

    try:
        doc = await ingestion_service.ingest_pdf(
            file_bytes=file_bytes,
            filename=file.filename,
            session=session,
            title=title,
        )
        return DocumentResponse(
            id=doc.id,
            title=doc.title,
            filename=doc.filename,
            total_pages=doc.total_pages,
            total_chunks=doc.total_chunks,
            metadata=doc.metadata_,
            created_at=doc.created_at,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar e indexar o PDF: {str(e)}",
        )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all indexed marketing documents",
)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Document).order_by(desc(Document.created_at)).offset(skip).limit(limit)
    result = await session.execute(stmt)
    docs = result.scalars().all()

    # Conta total
    count_stmt = select(Document)
    count_result = await session.execute(count_stmt)
    total = len(count_result.scalars().all())

    doc_responses = [
        DocumentResponse(
            id=d.id,
            title=d.title,
            filename=d.filename,
            total_pages=d.total_pages,
            total_chunks=d.total_chunks,
            metadata=d.metadata_,
            created_at=d.created_at,
        )
        for d in docs
    ]

    return DocumentListResponse(documents=doc_responses, total_count=total)


@router.get(
    "/{document_id}/chunks",
    response_model=List[DocumentChunkResponse],
    summary="List chunks of a specific document",
)
async def get_document_chunks(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    res = await session.execute(stmt)
    chunks = res.scalars().all()

    if not chunks:
        # Verifica se o documento existe
        doc_stmt = select(Document).where(Document.id == document_id)
        doc_res = await session.execute(doc_stmt)
        if not doc_res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento não encontrado.",
            )

    return [
        DocumentChunkResponse(
            id=c.id,
            chunk_index=c.chunk_index,
            page_number=c.page_number,
            section_title=c.section_title,
            content=c.content,
            metadata=c.metadata_,
        )
        for c in chunks
    ]


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and all associated chunks",
)
async def delete_document(
    document_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(Document.id == document_id)
    res = await session.execute(stmt)
    doc = res.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado.",
        )

    await session.delete(doc)
    await session.commit()
    return None
