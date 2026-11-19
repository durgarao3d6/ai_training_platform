"""AITMS API entry point (modular monolith)."""

from fastapi import FastAPI

from app.api.v1 import router as v1_router
from app.core.errors import register_error_handlers

app = FastAPI(title="AITMS API", version="0.1.0", openapi_url="/api/v1/openapi.json")
register_error_handlers(app)
app.include_router(v1_router)


@app.get("/healthz", tags=["system"])
def healthz() -> dict[str, str]:
    return {"status": "ok"}
