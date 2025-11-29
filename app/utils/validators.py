from typing import Tuple, Dict, Any, Optional
from pydantic import ValidationError
from app.models.requests import OPERATION_PAYLOAD_MAP


def validate_operation_type(operation_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate operation type is supported.
    
    Returns:
        (is_valid, error_message)
    """
    if operation_type not in OPERATION_PAYLOAD_MAP:
        valid_ops = ", ".join(OPERATION_PAYLOAD_MAP.keys())
        return False, f"Unknown operationType '{operation_type}'. Valid: {valid_ops}"
    
    return True, None


def validate_payload(operation_type: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate payload against operation schema.
    
    Returns:
        (is_valid, error_message, validation_errors_dict)
    """
    payload_model = OPERATION_PAYLOAD_MAP.get(operation_type)
    
    if not payload_model:
        return False, "Unknown operation type", None
    
    try:
        validated = payload_model(**payload)
        return True, None, None, validated
    
    except ValidationError as e:
        errors = e.errors()
        error_dict = {}
        
        for error in errors:
            field = ".".join(str(x) for x in error["loc"])
            error_dict[field] = {
                "type": error["type"],
                "message": error["msg"]
            }
        
        error_msg = f"Payload validation failed for {operation_type}"
        return False, error_msg, error_dict, None