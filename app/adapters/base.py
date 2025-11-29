from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class AdapterResponse:
    """Response from adapter."""
    data: Any
    status_code: int
    latency_ms: int
    upstream_url: str


class SportsProvider(ABC):
    """Abstract base class for sports data providers."""
    
    @abstractmethod
    async def list_leagues(self) -> AdapterResponse:
        """Get all available leagues."""
        pass
    
    @abstractmethod
    async def get_league_matches(self, league_id: int, season: Optional[int] = None) -> AdapterResponse:
        """Get matches for a specific league."""
        pass
    
    @abstractmethod
    async def get_team(self, team_id: int) -> AdapterResponse:
        """Get team information."""
        pass
    
    @abstractmethod
    async def get_matches_between_teams(self, team_id1: int, team_id_2: int) -> AdapterResponse:
        """Get match data between two specific teams."""
        pass
    
    