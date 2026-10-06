# Product Requirements Document (PRD)
# Enterprise Marketing Knowledge Agent

---

## 1. Visão Geral do Produto e Objetivos

### 1.1 Contexto e Justificativa
Em ambientes corporativos e agências de marketing, equipes lidam semanalmente com dezenas de relatórios em formato PDF (desempenho de campanhas de mídia paga, Google Ads, Meta Ads, relatórios de SEO, análises trimestrais de ROI/ROAS e CAC). 
Esses documentos combinam **narrativa textual** e **dados tabulares densos**. A análise manual é lenta, propensa a erros e dificulta a correlação rápida entre métricas e estratégias adotadas.

O **Enterprise Marketing Knowledge Agent** é um agente autônomo baseado em **Retrieval-Augmented Generation (RAG)** e **Visualização de Dados Dinâmica**. Ele ingere documentos internos corporativos em PDF, indexa o conteúdo em um banco relacional vetorial e responde dúvidas em linguagem natural com **respostas aterradas e citações exatas**, além de **gerar e renderizar gráficos interativos automaticamente** para métricas mencionadas nos relatórios.

### 1.2 Objetivos Principais
- **Objetivo Primário do Usuário**: Fazer perguntas analíticas complexas sobre documentos de marketing (ex: *"Compare o ROAS e o CAC do Google Ads vs Meta Ads no terceiro trimestre"*), recebendo respostas explicativas fundamentadas e gráficos visuais instantâneos.
- **Objetivo Estratégico (Entrevista Técnica)**: Demonstrar proficiência sênior em:
  - Arquitetura RAG avançada (Two-Stage Retrieval com busca híbrida densa + esparsa e reranking com Cross-Encoder).
  - Controle de fluxo e grafos cíclicos com **LangGraph** (Self-Reflective / CRAG com detecção de alucinação e reescrita de query).
  - Engenharia de Dados & SQL com **PostgreSQL 16**, **pgvector** e **Alembic**.
  - Engenharia de Prompts e **Structured Outputs** via Pydantic.
  - Desenvolvimento full-stack moderno com **FastAPI** assíncrono e **React + TypeScript + Vite + Recharts**.
  - Metodologia de avaliação automatizada com **RAG Triad Evals** em **pytest**.

---

## 2. Personas e Casos de Uso

### 2.1 Personas
1. **Analista / Coordenador de Marketing (Usuário Final)**:
   - Precisa consultar rapidamente KPIs de campanhas históricas sem ter que abrir múltiplos PDFs de 30 páginas.
   - Valoriza respostas diretas com indicação da página e arquivo de onde o dado veio.
   - Precisa de gráficos visuais prontos para colar em apresentações executivas.
2. **Engenheiro de IA / Avaliador Técnico (Entrevistador)**:
   - Avalia a solidez das decisões arquiteturais: separação de camadas, tratamento de erros, prevenção de alucinações, modelagem relacional + vetorial e qualidade do código.

### 2.2 Casos de Uso Principais (User Stories)
- **UC01 - Ingestão e Indexação de Relatório**:
  *Como* analista, *quero* fazer upload de um relatório em PDF via interface web, *para que* o sistema processe o texto, extraia as tabelas preservando a estrutura, gere os embeddings e indexe tudo no banco de dados.
- **UC02 - Pergunta Analítica com Geração de Gráfico**:
  *Como* analista, *quero* perguntar sobre a evolução mensal do investimento em mídia paga, *para que* o agente retorne a resposta textual detalhada e renderize um gráfico de barras/linhas no painel lateral.
- **UC03 - Citação e Rastreabilidade de Fontes**:
  *Como* analista, *quero* clicar nas referências citadas na resposta, *para que* eu veja o trecho exato, número da página e nome do arquivo de origem.
- **UC04 - Auto-Correção e Resiliência contra Consultas Ambíguas**:
  *Como* analista, se eu fizer uma pergunta genérica ou com termos incompletos, *o agente deve* avaliar internamente os documentos recuperados e, se forem insuficientes, reescrever a busca antes de gerar a resposta.

---

## 3. Requisitos Funcionais (RF)

### 3.1 Módulo de Ingestão e Processamento de Documentos
- **RF01.1 - Upload Multipart**: Endpoint `/api/v1/documents/upload` aceitando arquivos PDF de até 50MB.
- **RF01.2 - Extração com PyMuPDF**:
  - Extrair blocos de texto mantendo hierarquia de títulos (baseado em pesos e tamanhos relativos de fontes).
  - Detectar e extrair estruturas tabulares convertendo-as em formato Markdown tabular (`| Coluna | ... |`), garantindo integridade de linhas.
- **RF01.3 - Chunking Semântico Estruturado**:
  - Divisão de conteúdo em chunks de ~500 a 700 tokens com overlap de 100 tokens.
  - Fronteiras de chunking que respeitam parágrafos e tabelas (não cortar tabelas ao meio).
  - Herança de metadados ricos: `document_id`, `filename`, `page_number`, `section_title`, `chunk_index`, flags (`has_table`).
- **RF01.4 - Geração de Embeddings e Armazenamento**:
  - Gerar embeddings via OpenAI `text-embedding-3-small` (1536 dimensões).
  - Persistir chunks na tabela `document_chunks` com coluna vetorial `vector(1536)` e coluna léxica `tsvector`.

### 3.2 Módulo de Recuperação em 2 Etapas (Two-Stage Retrieval)
- **RF02.1 - Busca Vetorial Densa (Dense Search)**:
  - Consulta aos Top-20 chunks mais próximos via distância de cosseno (`<=>`) usando o índice HNSW.
- **RF02.2 - Busca Full-Text Esparsa (Sparse Search)**:
  - Consulta léxica aos Top-20 chunks via `ts_rank_cd` em português/inglês com `websearch_to_tsquery`.
- **RF02.3 - Fusão via Reciprocal Rank Fusion (RRF)**:
  - Fusão determinística dos rankings das buscas densa e esparsa com constante de suavização $k=60$:
    $$RRF\_Score(d) = \sum_{m \in \{dense, sparse\}} \frac{1}{60 + rank_m(d)}$$
  - Seleção dos Top-15 candidatos mais relevantes.
- **RF02.4 - Reranking com Cross-Encoder (FlashRank)**:
  - Modelo local `ms-marco-TinyBERT-L-2-v2` reordena os 15 candidatos com base no par `(query, chunk_text)`.
  - Retorno dos Top-4 a 5 chunks com score de relevância calibrado.

### 3.3 Módulo do Agente Inteligente (LangGraph CRAG)
- **RF03.1 - Roteamento Inicial (Router Node)**:
  - Classificar a mensagem do usuário: `DIRECT_REPLY` (saudação/fora de escopo) vs `RETRIEVE_KNOWLEDGE` (pergunta sobre marketing/documentos).
- **RF03.2 - Nó de Recuperação e Rerank**:
  - Acionar o motor de busca híbrida e atualizar o estado do grafo (`retrieved_docs`).
- **RF03.3 - Avaliador de Relevância (Grader Node)**:
  - Avaliar se o contexto recuperado é suficiente para responder à pergunta.
  - Se suficiente $\rightarrow$ encaminha para geração.
  - Se insuficiente e `retry_count < 2` $\rightarrow$ encaminha para reescrita de query.
  - Se atingiu o limite de tentativas $\rightarrow$ gera resposta informando limitação de contexto.
- **RF03.4 - Reescritor de Query (Rewriter Node)**:
  - Reformular a consulta decompondo acrônimos ou expandindo sinônimos de métricas de marketing.
- **RF03.5 - Gerador e Extrator de Gráficos (Generator Node)**:
  - Gerar resposta em Markdown aterrada nos fatos.
  - Extrair esquema estruturado via Pydantic (`ChartDataset`):
    - `chart_type`: `bar`, `line`, `area` ou `pie`.
    - `title`, `x_axis_key`, `data_keys`, `series_labels` e array `data`.

### 3.4 Módulo de API REST (FastAPI)
- **RF04.1 - Endpoint `/api/v1/health`**: Verificação de status da API e conexão com banco de dados.
- **RF04.2 - Endpoint `/api/v1/documents`**: Listagem de documentos ingeridos, quantidade de páginas, chunks e data de upload.
- **RF04.3 - Endpoint `/api/v1/documents/{id}`**: Exclusão e detalhes do documento.
- **RF04.4 - Endpoint `/api/v1/chat`**: Processamento de mensagem do usuário, executando o agente LangGraph e retornando resposta, fontes e gráfico.

### 3.5 Módulo de Frontend (React + TypeScript + Vite + Recharts)
- **RF05.1 - Interface Split-Screen**:
  - Painel esquerdo: Thread de chat com histórico, balões de mensagem estilizados, indicador de loading de raciocínio e citações expansíveis.
  - Painel direito: Aba 1 (Gerenciador de Documentos com drag-and-drop de PDF) e Aba 2 (Visualizador Expandido de Dados/Gráficos interativos).
- **RF05.2 - Renderização Dinâmica de Gráficos**:
  - Componente Recharts que lê o payload do backend e renderiza dinamicamente:
    - Gráfico de Barras (`BarChart`) para comparações entre canais.
    - Gráfico de Linhas / Área (`LineChart` / `AreaChart`) para evolução temporal de KPIs.
    - Gráfico de Pizza (`PieChart`) para distribuição de budget/investimento.
  - Tooltips formatados com valores percentuais e monetários (R$ / US$).

---

## 4. Requisitos Não-Funcionais (RNF)

- **RNF01 - Latência e Performance**:
  - O processamento de busca híbrida + rerank deve executar em menos de **300ms** no banco de dados local.
  - O pipeline completo do agente (incluindo chamadas ao LLM) deve responder em menos de **4.0 segundos** para consultas padrão.
- **RNF02 - Precisão e Aterramento (Zero Alucinações)**:
  - O prompt de geração deve conter instruções rígidas de aterramento: o modelo não deve inventar dados numéricos inexistentes nos chunks.
- **RNF03 - Portabilidade e Infraestrutura**:
  - O ambiente de banco de dados deve subir em 1 comando com Docker Compose (`docker compose up -d`).
  - Nenhuma dependência externa de infraestrutura paga deve ser exigida para além da chave da OpenAI.
- **RNF04 - Design e Acessibilidade Visual**:
  - Interface Dark Mode premium com paleta refinada (fundo escuro neutro, acentos ciano/esmeralda, contraste WCAG AA).
  - Tipografia moderna (Inter / Outfit) e animações suaves de transição.
- **RNF05 - Testabilidade e Observabilidade**:
  - Cobertura de testes unitários para o chunker, extrator de tabelas e algoritmo de RRF.
  - Suite de avaliação automatizada com métricas de RAG Triad.

---

## 5. Pré-requisitos, Ferramentas e Base a ser Configurada

### 5.1 Ferramentas do Sistema (Instaladas na Máquina)
- **Python**: Versão `>= 3.11` (Ambiente local possui Python 3.12.10).
- **Poetry**: Versão `>= 2.0` (Ambiente local possui Poetry 2.4.1).
- **Node.js**: Versão `>= 20.0` (Ambiente local possui Node v24.18.0 e npm 11.16.0).
- **Docker & Docker Compose**: Versão `>= 27.0` (Ambiente local possui Docker 29.8.2).
- **Git**: Configurado com remote `https://github.com/Alberanif/rag_marketing_agent.git`.

### 5.2 Variáveis de Ambiente Necessárias (`.env`)
```bash
# Provedores de IA
OPENAI_API_KEY="sk-..."
EMBEDDING_MODEL="text-embedding-3-small"
LLM_MODEL="gpt-4o-mini"

# Banco de Dados PostgreSQL + pgvector
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="marketing_agent_secret"
POSTGRES_DB="marketing_agent_db"
POSTGRES_HOST="localhost"
POSTGRES_PORT="5432"
DATABASE_URL="postgresql+asyncpg://postgres:marketing_agent_secret@localhost:5432/marketing_agent_db"

# Aplicação Backend
APP_ENV="development"
PORT="8000"
CORS_ORIGINS="http://localhost:5173,http://localhost:3000"
```

### 5.3 Dependências Principais do Backend (`pyproject.toml`)
- `fastapi` e `uvicorn` para servidor REST assíncrono.
- `sqlalchemy` (v2.0+) e `asyncpg` para ORM assíncrono.
- `pgvector` para integração vetorial com SQLAlchemy.
- `alembic` para controle de versão de migrações de banco.
- `pydantic` e `pydantic-settings` para validação e tipagem.
- `pymupdf` (`fitz`) para parsing e extração de PDFs e tabelas.
- `openai` para embeddings e inferência.
- `langgraph` e `langchain-core` para o agente de fluxo cíclico.
- `flashrank` para o reranker local cross-encoder ultra-rápido.
- `pytest` e `pytest-asyncio` para testes unitários e de integração.

### 5.4 Dependências Principais do Frontend (`package.json`)
- `react` e `react-dom` (v18+).
- `typescript` para tipagem estrita de componentes e requisições.
- `vite` para compilação ultra-rápida.
- `recharts` para renderização declarativa de gráficos responsivos.
- `lucide-react` para iconografia moderna.
- `axios` para comunicação com os endpoints da FastAPI.

---

## 6. Critérios de Aceite por Etapa de Implementação

| Fase | Entregável | Critério de Aceite |
| :--- | :--- | :--- |
| **Fase 1** | Infraestrutura & Docker | `docker compose up -d` sobe PostgreSQL 16 com extensão `vector` ativa e saudável na porta 5432. |
| **Fase 2** | Modelagem & Migrações | Alembic aplica migrações criando tabelas `documents` e `document_chunks` com índices HNSW e GIN. |
| **Fase 3** | Ingestão com PyMuPDF | Script ingere um PDF de marketing de exemplo, extrai tabelas em Markdown e gera chunks semânticos com embeddings válidos no banco. |
| **Fase 4** | Two-Stage Retrieval | Consulta por termo exato e semântico executa RRF e FlashRank, retornando os Top-4 chunks em menos de 300ms. |
| **Fase 5** | LangGraph Agent | Grafo executa fluxo completo (Router $\rightarrow$ Retrieve $\rightarrow$ Grade $\rightarrow$ Generate com Pydantic `AgentResponse` contendo resposta e payload de gráfico). |
| **Fase 6** | FastAPI Endpoints | Endpoints `/upload`, `/documents` e `/chat` testados com sucesso via Swagger (`/docs`). |
| **Fase 7** | Frontend Split-Screen | Interface React permite upload de documento, envio de mensagens e renderização de gráficos interativos (Recharts) com tooltips funcionais. |
| **Fase 8** | Quality & Evals | `poetry run pytest` passa 100% dos testes unitários e executa o RAG Triad Eval exibindo relatório de métricas no console. |

---

## 7. Matriz de Riscos e Mitigações

| Risco Identificado | Impacto | Mitigação Técnica |
| :--- | :--- | :--- |
| PDFs com layouts complexos em múltiplas colunas quebrando a ordem de leitura. | Médio | PyMuPDF com ordenação estrutural de blocos por coordenadas verticais/horizontais (`sort=True`). |
| Resposta do LLM gerando gráfico com formato inválido para o Recharts. | Alto | Validação rigorosa via Pydantic `with_structured_output` garantindo schema exato com fallback gracioso no frontend se o gráfico for nulo. |
| Falta de chave de API em ambiente de entrevista técnica. | Alto | Estrutura modular permitindo chave OpenAI via `.env` ou modo de teste/mock determinístico para demonstração offline. |
| Sobrecarga de memória em consultas concorrentes com Cross-Encoder. | Baixo | Uso do modelo quantizado ONNX do FlashRank (`ms-marco-TinyBERT-L-2-v2`), que consome menos de 40MB de RAM. |
