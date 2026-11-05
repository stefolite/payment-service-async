
from fastapi import FastAPI, Depends
from backend.core.config import Settings
from backend.core.security import verify_api_key
from backend.api.router import api_router


settings = Settings()
app = FastAPI(title=settings.app_name)
app.include_router(api_router)


@app.get("/health", dependencies=[Depends(verify_api_key)])
def check_health():
    return {"status": "ok"}
