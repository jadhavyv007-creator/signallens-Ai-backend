"""
Pytest configuration and test setup fixtures.
"""

import pytest
from api.database.db import init_db


@pytest.fixture(autouse=True, scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def setup_test_db():
    await init_db()


@pytest.fixture
async def async_db_session():
    from api.database.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session
