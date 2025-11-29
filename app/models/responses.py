from typing import Any, Optional, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code (e.g., VALIDATION_ERROR)")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ResponseMetadata(BaseModel):
    provider: str = Field(..., description="Provider name (e.g., 'openliga')")
    upstreamLatency: int = Field(..., ge=0, description="Upstream API latency in ms")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")


class SuccessResponse(BaseModel):
    requestId: str = Field(..., description="Request ID")
    success: bool = Field(True, description="Success flag")
    data: Any = Field(..., description="Response data (normalized)")
    metadata: ResponseMetadata = Field(..., description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "requestId": "550e8400-e29b-41d4-a716-446655440000",
                "success": True,
                "data": [
                    {
                        "id": 1,
                        "name": "Bundesliga",
                        "country": "Germany"
                    }
                ],
                "metadata": {
                    "provider": "openliga",
                    "upstreamLatency": 245,
                    "timestamp": "2024-01-22T10:30:00Z"
                }
            }
        }


class ErrorResponse(BaseModel):
    requestId: str = Field(..., description="Request ID")
    success: bool = Field(False, description="Success flag")
    error: ErrorDetail = Field(..., description="Error details")
    metadata: Optional[ResponseMetadata] = Field(None, description="Response metadata (if available)")

    class Config:
        json_schema_extra = {
            "example": {
                "requestId": "550e8400-e29b-41d4-a716-446655440000",
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Missing required field: leagueId",
                    "details": {
                        "field": "leagueId",
                        "reason": "required"
                    }
                },
                "metadata": None
            }
        }


class LeagueData(BaseModel):
    """Normalized league data."""
    id: int
    name: str
    country: str


class TeamData(BaseModel):
    """Normalized team data."""
    id: int
    name: str
    shortName: Optional[str] = None
    foundedYear: Optional[int] = None


class MatchData(BaseModel):
    id: int
    team1: str
    team2: str
    date: str
    status: str
    result: Optional[Dict[str, int]] = None
    goals1: Optional[int] = None
    goals2: Optional[int] = None