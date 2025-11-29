from typing import Optional, Literal
from pydantic import BaseModel, Field
from uuid import uuid4


class ListLeaguesPayload(BaseModel):
    """GET /api/getavailableleagues"""
    pass


class GetLeagueMatchesPayload(BaseModel):
    """GET /api/getmatchdata/{leagueId} or /{leagueId}/{season}"""
    leagueId: int = Field(..., gt=0, description="League ID")
    season: int = Field(..., gt=0, description="League ID")


class GetTeamPayload(BaseModel):
    """GET /api/getteam/{teamId}"""
    teamId: int = Field(..., gt=0, description="Team ID")


class GetMatchPayload(BaseModel):
    """GET /api/getmatchdata/{teamId1}/{teamId2}"""
    teamId1: int = Field(..., gt=0, description="Team 1 ID")
    teamId2: int = Field(..., gt=0, description="Team 2 ID")


OPERATION_PAYLOAD_MAP = {
    "ListLeagues": ListLeaguesPayload,
    "GetLeagueMatches": GetLeagueMatchesPayload,
    "GetTeam": GetTeamPayload,
    "GetMatch": GetMatchPayload
}

VALID_OPERATIONS = set(OPERATION_PAYLOAD_MAP.keys())


class ProxyRequest(BaseModel):
    operationType: Literal[
        "ListLeagues",
        "GetLeagueMatches",
        "GetTeam",
        "GetMatch",
    ] = Field(..., description="Type of operation to execute")

    requestId: Optional[str] = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique request ID (auto-generated if not provided)"
    )

    payload: dict = Field(
        ...,
        description="Operation-specific payload"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "operationType": "GetLeagueMatches",
                "payload": {
                    "leagueId": 123,
                    "season": 2025
                }
            }
        }
