from fastapi import FastAPI
from backend.core.config import Settings


settings = Settings()
app = FastAPI(title=settings.app_name)


@app.get("/health")
def check_health():
    return {"status": "ok"}
