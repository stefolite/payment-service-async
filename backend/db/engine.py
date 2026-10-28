from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config import Settings


settings = Settings()


engine = create_async_engine(settings.database_url)
