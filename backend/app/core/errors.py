import logging
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("docusense")

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={
            "error": {"code": "HTTP_ERROR", "message": str(exc.detail),
                      "path": request.url.path}
        }, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={
            "error": {"code": "VALIDATION_ERROR",
                      "message": "The request did not match the expected format.",
                      "details": exc.errors(), "path": request.url.path}
        })

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error at %s", request.url.path)
        return JSONResponse(status_code=500, content={
            "error": {"code": "INTERNAL_SERVER_ERROR",
                      "message": "An unexpected server error occurred.",
                      "path": request.url.path}
        })
