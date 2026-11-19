"""Smart Knowledge Portal reference app stub. Defect catalogue arrives in task 7.3."""

from fastapi import FastAPI

app = FastAPI(title="Smart Knowledge Portal (stub)")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
