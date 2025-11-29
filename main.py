import structlog
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.config import settings
from app.routes.proxy import router as proxy_router
from app.middleware.audit import AuditMiddleware
from app.adapters.manager import register_adapter
from app.adapters.openligadb import OpenLigaDBAdapter

register_adapter('openliga', OpenLigaDBAdapter)

structlog.configure(
    processors=[
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

app = FastAPI(
    title="OpenLiga Reverse Proxy",
    description="Generic reverse proxy to OpenLigaDB API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.add_middleware(AuditMiddleware)

@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "openliga-proxy",
        "version": "0.1.0"
    }

app.include_router(proxy_router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured response."""
    
    # If detail is already a dict (from our code), use it
    if isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    
    # Otherwise, wrap in error response
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "requestId": request.headers.get("X-Request-ID", "unknown"),
            "success": False,
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "details": None
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    await logger.aerror(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "requestId": request.headers.get("X-Request-ID", "unknown"),
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "details": None
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )