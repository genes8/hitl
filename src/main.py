import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.v1.router import router as v1_router

logger = logging.getLogger("hitl.api")


def create_app() -> FastAPI:
    app = FastAPI(title="HITL Credit Approval System API")

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        """Attach a request id to every response and log a compact access line.

        - If the caller provides X-Request-ID, we reuse it.
        - Otherwise we generate a UUID4.

        This is intentionally lightweight (Phase 1) but helps correlate logs.
        """

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "access request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    def _request_id_from_request(request: Request) -> str | None:
        return getattr(request.state, "request_id", None)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = _request_id_from_request(request)
        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "request_id": request_id,
            },
        )
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = _request_id_from_request(request)
        response = JSONResponse(
            status_code=422,
            content={
                "detail": exc.errors(),
                "request_id": request_id,
            },
        )
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = _request_id_from_request(request)
        logger.exception("unhandled_error request_id=%s", request_id, exc_info=exc)
        response = JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "request_id": request_id,
            },
        )
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(v1_router, prefix="/api/v1")
    return app


app = create_app()
