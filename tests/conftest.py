import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from fakeredis import aioredis as fakeredis

from src.main import app
from src.storage import storage
from src.config import settings

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest_asyncio.fixture
async def redis_client():
    """Provide fake Redis client for testing."""
    fake_redis = await fakeredis.FakeRedis(decode_responses=True)
    yield fake_redis
    await fake_redis.flushall()
    await fake_redis.aclose()


@pytest_asyncio.fixture
async def test_storage(redis_client):
    """Provide storage instance with fake Redis."""
    storage.client = redis_client
    yield storage


@pytest_asyncio.fixture
async def client(test_storage):
    """Provide async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_url():
    """Provide sample URL for testing."""
    return "https://www.example.com/very/long/url/path"


@pytest.fixture
def sample_url_data(sample_url):
    """Provide sample URL creation data."""
    return {"url": sample_url}
