from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rich.console import Console

from backend.app.api.router import api_router
from backend.app.config import get_settings

settings = get_settings()
console = Console()


@asynccontextmanager
async def lifespan(app: FastAPI):
    console.print(
        "[bold cyan]Enterprise Marketing Knowledge Agent (Lola)[/bold cyan] inicializado."
    )
    yield
    console.print(
        "[bold yellow]Enterprise Marketing Knowledge Agent[/bold yellow] finalizado."
    )


app = FastAPI(
    title="Enterprise Marketing Knowledge Agent (Lola)",
    description=(
        "API para Ingestão de Relatórios Corporativos, Recuperação em 2 Etapas "
        "(pgvector + FTS com RRF e FlashRank) e Agente Lola (LangGraph CRAG) "
        "com extração estruturada para Recharts."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conecta rotas da API
app.include_router(api_router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "Enterprise Marketing Knowledge Agent API",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
    }
