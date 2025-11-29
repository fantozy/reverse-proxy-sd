import time
import json
import uuid
import structlog
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from fastapi.responses import StreamingResponse, FileResponse

logger = structlog.get_logger()


class AuditMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        request_id = await self._get_or_generate_request_id(request)
        method = request.method
        path = request.url.path
        
        await self._log_inbound(request, request_id, method, path)
        
        try:
            response = await call_next(request)
            latency_ms = int((time.time() - start_time) * 1000)
            await self._log_outbound(response, request_id, latency_ms)
            
            return response
        
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            await logger.aerror(
                "request_error",
                request_id=request_id,
                method=method,
                path=path,
                error=str(e),
                latency_ms=latency_ms
            )
            raise
    
    async def _log_inbound(self, request: Request, request_id: str, method: str, path: str):
        safe_headers = {}
        unsafe_header_keys = {"authorization", "x-api-key", "cookie", "x-token"}
        
        for key, value in request.headers.items():
            if key.lower() not in unsafe_header_keys:
                safe_headers[key] = value
        
        body_size = 0
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                body_size = len(body)
                
                # For logging, truncate body
                body_preview = body.decode("utf-8", errors="ignore")[:settings.LOG_BODY_LIMIT]
            except:
                body_preview = ""
        else:
            body_preview = ""
        
        await logger.ainfo(
            "inbound_request",
            request_id=request_id,
            method=method,
            path=path,
            headers=safe_headers,
            body_size=body_size,
            body_preview=body_preview if body_preview else None
        )
    
    async def _log_outbound(self, response: Response, request_id: str, latency_ms: int):
        if isinstance(response, (StreamingResponse, FileResponse)):
            body_size = 0
        elif hasattr(response, 'body'):
            body_size = len(response.body) if response.body else 0
        else:
            body_size = 0

        await logger.ainfo(
            "outbound_response",
            request_id=request_id,
            status_code=response.status_code,
            body_size=body_size,
            latency_ms=latency_ms
        )
        
    async def _get_or_generate_request_id(self, request: Request) -> str:
        request_id = request.headers.get("X-Request-ID")
        if request_id:
            return request_id
        
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    data = json.loads(body)
                    if isinstance(data, dict) and "requestId" in data:
                        return data["requestId"]
            except (json.JSONDecodeError, Exception):
                pass
        
        return str(uuid.uuid4())


