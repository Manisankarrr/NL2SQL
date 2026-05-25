from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from backend.middleware.logger import pipeline_logger
import logging, traceback

logger = logging.getLogger("barbersql.errors")

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    pipeline_logger.warn(f"Validation error on {request.url.path}: {exc.errors()[0].get('msg','')}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid request format",
            "details": str(exc.errors()[0].get("msg", "Unknown validation error")),
            "path": str(request.url.path)
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    pipeline_logger.warn(f"HTTP {exc.status_code} on {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    pipeline_logger.error(f"Unhandled exception on {request.url.path}", exc=exc)
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "type": type(exc).__name__,
            "message": "Something went wrong. Check backend logs."
        }
    )

def register_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
