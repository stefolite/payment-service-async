from fastapi import FastAPI
from backend.core.config import Settings
from backend.api.router import api_router


settings = Settings()
app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.get("/health")
def check_health():
    return {"status": "ok"}
