"""Sandbox runner stub. Real container execution arrives in Phase 4b (task 6.1)."""

from fastapi import FastAPI

app = FastAPI(title="AITMS Sandbox Runner (stub)")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
