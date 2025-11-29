import structlog
from fastapi import APIRouter, HTTPException, status
from app.models.requests import ProxyRequest
from app.models.responses import SuccessResponse, ErrorResponse, ResponseMetadata
from app.adapters.manager import get_adapter
from app.decision_mapper import DecisionMapper
from app.utils.validators import validate_operation_type, validate_payload 
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
    return _mapper


@router.post(
    "/execute",
    response_model=SuccessResponse | ErrorResponse,
    status_code=200
)
async def execute_proxy(request: ProxyRequest):
    """
    Main reverse proxy endpoint.
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "requestId": request_id,
                "success": False,
                "error": {
                    "code": "UNKNOWN_OPERATION",
                    "message": validation_error,
                    "details": None
                }
            }
        )
    
    is_valid, validation_error, error_details, validated_payload = validate_payload(operation_type, payload)
    if not is_valid:
        await logger.awarning(
            "validation_failed",
            request_id=request_id,
            operation_type=operation_type,
            error_type="payload_validation_error",
            error_message=validation_error,
            error_details=error_details
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "requestId": request_id,
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": validation_error,
                    "details": error_details
                }
            }
        )
    
    await logger.ainfo(
        "validation_passed",
        request_id=request_id,
        operation_type=operation_type
    )
    
    try:
        mapper = await get_mapper()
        adapter_response = await mapper.execute(operation_type, validated_payload)
        
        await logger.ainfo(
            "upstream_call",
            request_id=request_id,
            operation_type=operation_type,
            provider="openliga",
            target_url=adapter_response.upstream_url,
            status_code=adapter_response.status_code,
            latency_ms=adapter_response.latency_ms
        )
        
        if adapter_response.status_code != 200:
            await logger.aerror(
                "upstream_failed",
                request_id=request_id,
                operation_type=operation_type,
                status_code=adapter_response.status_code,
                error=adapter_response.data
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "requestId": request_id,
                    "success": False,
                    "error": {
                        "code": "UPSTREAM_ERROR",
                        "message": "Upstream API failed after retries",
                        "details": adapter_response.data
                    }
                }
            )
        
        metadata = ResponseMetadata(
            provider="openliga",
            upstreamLatency=adapter_response.latency_ms
        )
        
        success_response = SuccessResponse(
            requestId=request_id,
            success=True,
            data=adapter_response.data,
            metadata=metadata
        )
        
        await logger.ainfo(
            "proxy_request_success",
            request_id=request_id,
            operation_type=operation_type,
            data_items=len(adapter_response.data) if isinstance(adapter_response.data, list) else 1
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "requestId": request_id,
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "details": None
                }
            }
        )