import structlog
from fastapi import APIRouter, HTTPException, Request, status
from app.models.requests import ProxyRequest
from app.models.responses import SuccessResponse, ErrorResponse, ResponseMetadata
from app.adapters.manager import get_adapter
from app.decision_mapper import DecisionMapper, validate_operation_type, validate_payload
from app.normalizers import normalize_response
from app.config import settings


logger = structlog.get_logger()
router = APIRouter(prefix="/proxy", tags=["proxy"])

_mapper = None

async def get_mapper():
    """Get or initialize decision mapper with adapter."""
    global _mapper
    if _mapper is None:
        adapter = await get_adapter('openliga', settings)
        _mapper = DecisionMapper(adapter)
        _mapper.register_all()
    return _mapper


@router.post(
    "/execute",
    response_model=SuccessResponse | ErrorResponse,
    status_code=200
)
async def execute_proxy(request: ProxyRequest, raw_request: Request):
    """
    Main reverse proxy endpoint.
    Routes by operationType, validates payload, invokes decision mapper,
    and returns normalized response.
    """
    request_id = request.requestId
    operation_type = request.operationType
    payload = request.payload
    
    await logger.ainfo(
        "proxy_request_received",
        request_id=request_id,
        operation_type=operation_type
    )
    
    is_valid, validation_error = validate_operation_type(operation_type)
    if not is_valid:
        await logger.awarning(
            "validation_failed",
            request_id=request_id,
            operation_type=operation_type,
            error_type="unknown_operation_type",
            error_message=validation_error
        )
        raise _error_response(
            request_id, 400, "UNKNOWN_OPERATION", validation_error
        )
    
    is_valid, validation_error, error_details = validate_payload(operation_type, payload)
    if not is_valid:
        await logger.awarning(
            "validation_failed",
            request_id=request_id,
            operation_type=operation_type,
            error_type="payload_validation_error",
            error_message=validation_error,
            error_details=error_details
        )
        raise _error_response(
            request_id, 400, "VALIDATION_ERROR", validation_error, error_details
        )
    
    await logger.ainfo(
        "validation_passed",
        request_id=request_id,
        operation_type=operation_type
    )
    
    try:
        mapper = await get_mapper()
        decision = mapper.get_decision(operation_type)
        
        if not decision:
            raise ValueError(f"No decision found for operation: {operation_type}")
        
        adapter_response = await decision.execute(mapper.adapter, payload)
        upstream_latency = adapter_response.latency_ms
        
        await logger.ainfo(
            "upstream_call",
            request_id=request_id,
            operation_type=operation_type,
            provider="openliga",
            target_url=adapter_response.upstream_url,
            status_code=adapter_response.status_code,
            latency_ms=upstream_latency
        )
        
        if adapter_response.status_code != 200:
            await logger.aerror(
                "upstream_failed",
                request_id=request_id,
                operation_type=operation_type,
                status_code=adapter_response.status_code,
                error=adapter_response.data
            )
            raise _error_response(
                request_id, 502, "UPSTREAM_ERROR",
                "Upstream API failed after retries",
                adapter_response.data
            )
        
        normalized_data = normalize_response(operation_type, adapter_response.data)
        metadata = ResponseMetadata(
            provider="openliga",
            upstreamLatency=upstream_latency
        )
        
        success_response = SuccessResponse(
            requestId=request_id,
            success=True,
            data=normalized_data,
            metadata=metadata
        )
        
        await logger.ainfo(
            "proxy_request_success",
            request_id=request_id,
            operation_type=operation_type,
            data_items=len(normalized_data) if isinstance(normalized_data, list) else 1
        )
        
        return success_response
    
    except HTTPException:
        raise
    
    except Exception as e:
        await logger.aerror(
            "proxy_request_error",
            request_id=request_id,
            operation_type=operation_type,
            error=str(e),
            error_type=type(e).__name__
        )
        raise _error_response(
            request_id, 500, "INTERNAL_ERROR", "Internal server error"
        )


def _error_response(
    request_id: str,
    status_code: int,
    error_code: str,
    message: str,
    details: any = None
):
    """Helper to create standardized error responses."""
    http_status = {
        400: status.HTTP_400_BAD_REQUEST,
        502: status.HTTP_502_BAD_GATEWAY,
        500: status.HTTP_500_INTERNAL_SERVER_ERROR
    }.get(status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=http_status,
        detail={
            "requestId": request_id,
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details
            }
        }
    )