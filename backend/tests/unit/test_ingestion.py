import pytest
import fitz
from backend.app.ingestion.parser import PDFParser
from backend.app.ingestion.chunker import SemanticChunker
from backend.app.ingestion.service import IngestionService
from backend.app.database import AsyncSessionLocal
from backend.app.models.document import Document, DocumentChunk
from sqlalchemy import select


def create_sample_marketing_pdf_bytes() -> bytes:
    """Cria um PDF de marketing com títulos e tabelas para teste."""
    doc = fitz.open()
    page = doc.new_page()

    # Título H1
    page.insert_text((50, 60), "Relatório Executivo de Marketing - Q3 2026", fontsize=20)

    # Subtítulo H2
    page.insert_text((50, 100), "Desempenho Geral de Campanhas Pagas", fontsize=14)

    # Parágrafo com métricas
    text = (
        "No terceiro trimestre de 2026, as campanhas de Google Ads e Meta Ads "
        "apresentaram crescimento expressivo de conversões. O investimento total "
        "foi de R$ 150.000, gerando um ROAS médio de 4.8 e CAC de R$ 42,50."
    )
    page.insert_textbox(fitz.Rect(50, 120, 500, 200), text, fontsize=11)

    # Desenhar uma tabela simples
    # Linhas da tabela
    y = 230
    page.insert_text((50, y), "Canal", fontsize=11)
    page.insert_text((150, y), "Investimento", fontsize=11)
    page.insert_text((280, y), "ROAS", fontsize=11)
    page.insert_text((380, y), "CAC", fontsize=11)
    page.draw_line(fitz.Point(50, y + 5), fitz.Point(450, y + 5))

    rows = [
        ("Google Ads", "R$ 80.000", "5.2", "R$ 38,00"),
        ("Meta Ads", "R$ 50.000", "4.5", "R$ 44,00"),
        ("TikTok Ads", "R$ 20.000", "3.8", "R$ 52,00"),
    ]

    for canal, inv, roas, cac in rows:
        y += 25
        page.insert_text((50, y), canal, fontsize=10)
        page.insert_text((150, y), inv, fontsize=10)
        page.insert_text((280, y), roas, fontsize=10)
        page.insert_text((380, y), cac, fontsize=10)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_parser_extracts_headings_and_content():
    pdf_bytes = create_sample_marketing_pdf_bytes()
    parser = PDFParser()
    parsed = parser.parse_pdf(pdf_bytes, "relatorio_teste.pdf")

    assert parsed.total_pages == 1
    assert len(parsed.blocks) > 0
    # Verifica se encontrou títulos
    headings = [b for b in parsed.blocks if b.block_type == "heading"]
    assert len(headings) >= 1
    assert any("Marketing" in h.content for h in headings)


def test_chunker_detects_metrics_and_splits_responsibly():
    pdf_bytes = create_sample_marketing_pdf_bytes()
    parser = PDFParser()
    parsed = parser.parse_pdf(pdf_bytes, "relatorio_teste.pdf")

    chunker = SemanticChunker(target_tokens=200, overlap_tokens=40)
    chunks = chunker.chunk_document(parsed)

    assert len(chunks) >= 1
    first_chunk = chunks[0]
    assert first_chunk.token_count > 0
    assert "metrics_mentioned" in first_chunk.metadata
    metrics = first_chunk.metadata["metrics_mentioned"]
    assert "ROAS" in metrics or "CAC" in metrics or "INVESTIMENTO" in metrics


@pytest.mark.asyncio
async def test_ingestion_service_persists_in_postgres():
    pdf_bytes = create_sample_marketing_pdf_bytes()
    service = IngestionService()

    async with AsyncSessionLocal() as session:
        doc = await service.ingest_pdf(
            file_bytes=pdf_bytes,
            filename="relatorio_teste_marketing.pdf",
            session=session,
            title="Relatório Teste Q3",
        )

        assert doc.id is not None
        assert doc.total_chunks >= 1
        assert doc.total_pages == 1

        # Verifica chunks no banco
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        result = await session.execute(stmt)
        chunks = result.scalars().all()

        assert len(chunks) == doc.total_chunks
        assert chunks[0].embedding is not None
        assert len(chunks[0].embedding) == 1536
        assert chunks[0].section_title is not None
