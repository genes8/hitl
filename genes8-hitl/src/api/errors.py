import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("hitl.api")


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = _get_request_id(request)
        payload: dict = {"detail": exc.detail}
        if request_id:
            payload["request_id"] = request_id

        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = _get_request_id(request)
        payload: dict = {"detail": exc.errors()}
        if request_id:
            payload["request_id"] = request_id

        return JSONResponse(status_code=422, content=payload)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = _get_request_id(request)
        logger.exception("unhandled_exception request_id=%s", request_id)

        payload: dict = {"detail": "Internal Server Error"}
        if request_id:
            payload["request_id"] = request_id

        return JSONResponse(status_code=500, content=payload)
