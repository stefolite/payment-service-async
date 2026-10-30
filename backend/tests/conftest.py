import pytest
from backend.core.config import Settings
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
import pytest_asyncio
from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import delete
from backend.payments.models import Payment
from backend.outbox.models import Outbox


@pytest.fixture
def test_database_url():
    settings = Settings()

    database_url = settings.database_url
    database_name = make_url(database_url).database

    test_database_url = settings.test_database_url
    assert test_database_url is not None

    test_database_name = make_url(test_database_url).database
    assert test_database_name is not None

    assert test_database_name.endswith("_test")
    assert test_database_name != database_name

    return test_database_url


@pytest_asyncio.fixture
async def test_engine(test_database_url, migrated_database):
    test_engine = create_async_engine(test_database_url)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
def migrated_database(test_database_url):
    config = Config("alembic.ini")
    config.attributes["database_url"] = test_database_url
    command.upgrade(config, "head")


@pytest_asyncio.fixture
async def test_session(test_engine):
    async_factory = async_sessionmaker(
        test_engine,
        expire_on_commit=False
    )
    try:

        async with async_factory() as session:
            yield session

    finally:
        async with async_factory.begin() as session:
            await session.execute(delete(Payment))
            await session.execute(delete(Outbox))
