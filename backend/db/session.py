from backend.db.engine import engine
from sqlalchemy.ext.asyncio import async_sessionmaker


async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session():
    async with async_session_factory() as session:
        yield session
