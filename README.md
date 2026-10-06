# Lola: Enterprise Marketing Knowledge Agent

> **Agente Autônomo de Inteligência de Marketing com Recuperação Híbrida em 2 Etapas (pgvector + FTS com RRF e FlashRank), Grafo Auto-Reflexivo CRAG (LangGraph) e Visualização Interativa em Recharts.**

---

## 🏛️ Arquitetura do Sistema

```
[ Frontend: React + TypeScript + Vite + Recharts ] (Split-Screen Dark Mode)
                        │
                        ▼ (HTTP REST)
[ Backend: FastAPI + Uvicorn + Pydantic v2 ]
  ├── 1. Ingestão: PyMuPDF (Detecção de Títulos e Tabelas em Markdown) + Semantic Chunker (~600t)
  ├── 2. Recuperação em 2 Etapas:
  │     ├── Etapa 1: Busca Densa (pgvector <=>) + Busca Esparsa (FTS tsvector) ➔ RRF (k=60) Top-15
  │     └── Etapa 2: Cross-Encoder local FlashRank (ms-marco-TinyBERT-L-2-v2) ➔ Top-5
  ├── 3. Agente Lola (LangGraph CRAG):
  │     Router ➔ Retrieve ➔ Grader ➔ [Rewrite ➔ Retrieve] ➔ Generator ➔ Chart Extraction
  └── 4. Banco de Dados: PostgreSQL 16 + pgvector (Índices HNSW e GIN)
```

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
- **Docker & Docker Compose**
- **Python 3.12** com **Poetry**
- **Node.js 20+** com **npm**

---

### 1. Banco de Dados (PostgreSQL + pgvector)

Inicie o container do banco vetorial:
```bash
docker compose up -d
```
Verifique o status do container:
```bash
docker ps
```

---

### 2. Backend (FastAPI + LangGraph)

Instale as dependências:
```bash
poetry install
```

Execute as migrações do banco via Alembic:
```bash
poetry run alembic upgrade head
```

Inicie o servidor de desenvolvimento:
```bash
poetry run uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```
- **API Swagger / Documentação Interativa**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### 3. Frontend (React + TypeScript + Vite)

Navegue até a pasta do frontend e inicie o servidor:
```bash
cd frontend
npm install
npm run dev
```
- Acesse a interface web no navegador: [http://localhost:5173](http://localhost:5173)

---

## 🧪 Qualidade & Avaliação (RAG Triad Evals)

Execute a suite completa de testes unitários e avaliações:
```bash
# Executa todos os testes unitários (100% passando)
poetry run pytest

# Executa a suite de avaliação da Tríade de RAG com exibição tabular no console
poetry run pytest backend/tests/evals/test_rag_evals.py -s
```

### Resultados da Tríade de Avaliação (Golden Dataset):
- **Relevância de Contexto Média**: `0.81`
- **Fidelidade / Aterramento (Zero Alucinação)**: `0.96`
- **Relevância de Resposta Média**: `0.90`
- **Score Global da Tríade de RAG**: `0.89`

---

## 📦 Estrutura de Pastas

```text
MARKETING_AGENT/
├── docker-compose.yml           # PostgreSQL 16 + pgvector
├── pyproject.toml               # Dependências do backend via Poetry
├── alembic.ini                  # Configuração de versionamento do banco
│
├── backend/
│   ├── alembic/                 # Migrações de esquema (HNSW e GIN)
│   ├── app/
│   │   ├── main.py              # Entrypoint FastAPI
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # SQLAlchemy 2.0 Async Session & Engine
│   │   ├── models/              # Models ORM (Document, DocumentChunk)
│   │   ├── schemas/             # Schemas Pydantic (ChartDataset, AgentResponse, etc.)
│   │   ├── ingestion/           # PyMuPDF Parser & Semantic Chunker
│   │   ├── retrieval/           # Two-Stage Retrieval (RRF + FlashRank)
│   │   ├── agent/               # LangGraph Self-Reflective CRAG
│   │   └── api/                 # Endpoints REST (/documents, /chat, /health)
│   └── tests/
│       ├── unit/                # Testes de ingestão, busca, agente e API
│       └── evals/               # RAG Triad Evals com Golden Dataset
│
└── frontend/                    # Interface Split-Screen em React + Vite
    ├── src/
    │   ├── components/Chat/     # Chat conversacional com citações expansíveis
    │   ├── components/Visualizer/# Gráficos Recharts (Bar, Line, Area, Pie)
    │   ├── components/Documents/# Upload Drag & Drop e inspetor de chunks
    │   ├── services/api.ts      # Cliente Axios
    │   └── styles/index.css     # Design System Vanilla CSS (Dark Slate & Neon Cyan)
```
