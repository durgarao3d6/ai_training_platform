"""RFC 7807 problem+json errors (Architecture 14)."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_JSON = "application/problem+json"


def problem(status: int, title: str, detail: str | None = None, **extra: object) -> JSONResponse:
    body: dict[str, object] = {"type": "about:blank", "title": title, "status": status}
    if detail:
        body["detail"] = detail
    body.update(extra)
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON)


class ProblemError(Exception):
    """Raise from services to return a problem+json response with extra members (e.g. errors)."""

    def __init__(self, status: int, title: str, detail: str | None = None, **extra: object) -> None:
        super().__init__(title)
        self.status = status
        self.title = title
        self.detail = detail
        self.extra = extra


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(_: Request, exc: ProblemError) -> JSONResponse:
        return problem(exc.status, exc.title, exc.detail, **exc.extra)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(exc.status_code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return problem(
            422, "Validation error", "The request did not match the expected shape.", errors=errors
        )
