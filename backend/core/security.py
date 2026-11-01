from fastapi import Header
from backend.core.config import Settings
from hmac import compare_digest
from fastapi import HTTPException, status


settings = Settings()


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key is None or not compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
