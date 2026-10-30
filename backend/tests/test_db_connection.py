import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_database_connection(test_engine):
    async with test_engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        result = result.scalar_one()
        assert result == 1
