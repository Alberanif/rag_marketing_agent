import pytest
from backend.app.database import engine


@pytest.fixture(autouse=True)
async def cleanup_db_engine():
    """Garante que a pool de conexões do SQLAlchemy/asyncpg seja limpa entre event loops de teste."""
    yield
    await engine.dispose()
