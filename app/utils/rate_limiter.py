import time
from collections import deque
from typing import Deque
import structlog

from fastapi import HTTPException, status


logger = structlog.get_logger()


class RateLimiter:
    def __init__(self, limit: int, window: int):
        """
        Initialize rate limiter.
        
        Args:
            rpm: Requests per minute limit
        """
        self.limit = limit
        self.requests: Deque[float] = deque()
        self.window = window 
    
    def is_allowed(self) -> bool:
        """
        Check if request is allowed.
        
        Returns:
            True if request is within rate limit, False otherwise
        """
        current_time = time.monotonic()
        
        while self.requests and self.requests[0] < current_time - self.window:
            self.requests.popleft()
        
        # Check if we're within limit
        if len(self.requests) < self.limit:
            self.requests.append(current_time)
            return True
        
        return False
    
    def get_remaining(self) -> int:
        """Get number of remaining requests in current window."""
        current_time = time.monotonic()
        
        # Remove old requests
        while self.requests and self.requests[0] < current_time - self.window:
            self.requests.popleft()
        
        return max(0, self.limit - len(self.requests))
    
    def get_reset_time(self) -> float:
        """Get time until rate limit resets (in seconds)."""
        if not self.requests:
            return 0
        
        current_time = time.monotonic()
        oldest_request = self.requests[0]
        reset_time = oldest_request + self.window - current_time
        
        return max(0, reset_time)


async def check_rate_limit(rate_limiter: RateLimiter, adapter_name: str, request_id: str = ""):
    """Reusable rate limit check."""
    if not rate_limiter.is_allowed():
        remaining = rate_limiter.get_remaining()
        reset_time = rate_limiter.get_reset_time()
        await logger.awarning(
            "rate_limit_exceeded",
            adapter=adapter_name,
            request_id=request_id,
            remaining=remaining,
            reset_time_sec=reset_time
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit exceeded. Reset in {reset_time:.1f}s"
            }
        )
