from sqlalchemy.sql import text
import asyncio
from backend.db.engine import engine


async def main():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print(result.fetchone())
    await engine.dispose()


asyncio.run(main())
