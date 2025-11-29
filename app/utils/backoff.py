import random

def exponential_backoff(
    retry_count: int,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    jitter: bool = True
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.
    
    Args:
        retry_count: Number of retries so far (0-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter
    
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** retry_count), max_delay)
    
    if jitter:
        delay = random.uniform(0, delay)
    
    return delay