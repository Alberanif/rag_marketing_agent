import io
import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.tests.unit.test_ingestion import create_sample_marketing_pdf_bytes


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["pgvector"] == "active"


@pytest.mark.asyncio
async def test_documents_lifecycle_and_chat():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload de PDF
        pdf_bytes = create_sample_marketing_pdf_bytes()
        files = {
            "file": ("relatorio_api_teste.pdf", io.BytesIO(pdf_bytes), "application/pdf")
        }
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files=files,
            params={"title": "Relatório API Teste"},
        )
        assert upload_resp.status_code == 201, f"Error detail: {upload_resp.text}"
        doc_data = upload_resp.json()
        doc_id = doc_data["id"]
        assert doc_data["title"] == "Relatório API Teste"
        assert doc_data["total_chunks"] >= 1

        # 2. Listagem de documentos
        list_resp = await client.get("/api/v1/documents")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total_count"] >= 1
        assert any(d["id"] == doc_id for d in list_data["documents"])

        # 3. Listagem de chunks do documento
        chunks_resp = await client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert chunks_resp.status_code == 200
        chunks = chunks_resp.json()
        assert len(chunks) == doc_data["total_chunks"]

        # 4. Chat com o Agente Lola
        chat_resp = await client.post(
            "/api/v1/chat",
            json={"query": "Quais canais tiveram melhor ROAS no relatório?"},
        )
        assert chat_resp.status_code == 200
        chat_data = chat_resp.json()
        assert "answer_markdown" in chat_data
        assert len(chat_data["citations"]) > 0

        # 5. Exclusão do documento
        delete_resp = await client.delete(f"/api/v1/documents/{doc_id}")
        assert delete_resp.status_code == 204

        # 6. Verifica que não existe mais
        deleted_check = await client.get(f"/api/v1/documents/{doc_id}/chunks")
        assert deleted_check.status_code == 404
