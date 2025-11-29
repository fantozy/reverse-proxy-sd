import httpx
import time
import asyncio
from typing import Optional
from app.adapters.base import SportsProvider, AdapterResponse
from app.utils.backoff import exponential_backoff
from app.utils.rate_limiter import RateLimiter, check_rate_limit
import structlog

logger = structlog.get_logger()



class OpenLigaDBAdapter(SportsProvider):
    ADAPTER_NAME = 'openliga'
    
    """Adapter for OpenLigaDB API."""
    def __init__(self, settings):
        self.settings = settings
        limit = self.settings.RATE_LIMIT.get(self.ADAPTER_NAME) 
        window = self.settings.RATE_WINDOW.get(self.ADAPTER_NAME)
        self.rate_limiter = RateLimiter(limit, window)
        self.base_url = settings.OPENLIGADB_BASE_URL
        self.timeout = settings.OPENLIGADB_TIMEOUT
        self.client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=self.timeout)
        return self.client
    
    async def _fetch(self, url: str, retry_count: int = 0) -> AdapterResponse:
        """
        Fetch data from OpenLiga with exponential backoff retry logic.
        """
        await check_rate_limit(self.rate_limiter, "openliga")
        client = await self._get_client()
        
        try:
            start_time = time.time()
            response = await client.get(url, follow_redirects=True)
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                return AdapterResponse(
                    data=response.json(),
                    status_code=response.status_code,
                    latency_ms=latency_ms,
                    upstream_url=url
                )
            
            # Retry logic for transient errors (429, 5xx)
            if response.status_code in [429, 500, 502, 503, 504] and retry_count < self.settings.BACKOFF_MAX_RETRIES:
                await logger.ainfo(
                    "upstream_error_retry",
                    status_code=response.status_code,
                    retry_count=retry_count
                )
                
                delay = exponential_backoff(
                    retry_count,
                    base_delay=self.settings.BACKOFF_BASE_DELAY,
                    max_delay=self.settings.BACKOFF_MAX_DELAY,
                    jitter=self.settings.BACKOFF_JITTER
                )
                
                await asyncio.sleep(delay)
                return await self._fetch(url, retry_count + 1)
            
            # Non-retryable error
            return AdapterResponse(
                data={"error": f"API error: {response.status_code}"},
                status_code=response.status_code,
                latency_ms=latency_ms,
                upstream_url=url
            )
            
        except asyncio.TimeoutError:
            if retry_count < self.settings.BACKOFF_MAX_RETRIES:
                await logger.ainfo(
                    "upstream_timeout_retry",
                    retry_count=retry_count
                )
                
                delay = exponential_backoff(
                    retry_count,
                    base_delay=self.settings.BACKOFF_BASE_DELAY,
                    max_delay=self.settings.BACKOFF_MAX_DELAY,
                    jitter=self.settings.BACKOFF_JITTER
                )
                
                await asyncio.sleep(delay)
                return await self._fetch(url, retry_count + 1)
            
            return AdapterResponse(
                data={"error": "Request timeout"},
                status_code=504,
                latency_ms=int(self.timeout * 1000),
                upstream_url=url
            )
    
    async def list_leagues(self) -> AdapterResponse:
        """Get all available leagues."""
        url = f"{self.base_url}/api/getavailableleagues"
        return await self._fetch(url)
    
    async def get_league_matches(self, league_id: int, season: Optional[int] = None) -> AdapterResponse:
        """Get matches for a specific league."""
        url = f"{self.base_url}/api/getmatchdata/{league_id}/{season}"
        
        return await self._fetch(url)
    
    async def get_team(self, team_id: int) -> AdapterResponse:
        """Get team information."""
        url = f"{self.base_url}/api/getteam/{team_id}"
        return await self._fetch(url)
    
    async def get_league_standings(self, league_id: int) -> AdapterResponse:
        """Get standings for a specific league."""
        url = f"{self.base_url}/api/getbltable/{league_id}"
        return await self._fetch(url)
    
    async def get_matches_between_teams(self, team_id1: int, team_id2: int) -> AdapterResponse:
        """Get match data between two specific teams."""
        url = f"{self.base_url}/api/getmatchdata/{team_id1}/{team_id2}"
        return await self._fetch(url)
    
    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()
