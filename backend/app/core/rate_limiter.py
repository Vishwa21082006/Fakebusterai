"""
FakeBuster AI — Redis-based Sliding Window Rate Limiter
Protects endpoints from abuse with configurable per-route limits.
"""

from fastapi import HTTPException, Request, status
from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()

# Module-level Redis client — initialized in app lifespan
_redis_client: Redis | None = None


async def init_redis() -> Redis:
    """Initialize the Redis connection. Called during app startup."""
    global _redis_client
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    # Verify we can actually reach Redis (from_url is lazy)
    await client.ping()
    _redis_client = client
    return _redis_client


async def close_redis():
    """Close the Redis connection. Called during app shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def get_redis() -> Redis | None:
    """Get the active Redis client (or None if not initialized)."""
    return _redis_client


class RateLimiter:
    """
    Sliding-window rate limiter backed by Redis.
    Use as a FastAPI dependency:

        @app.post("/upload", dependencies=[Depends(RateLimiter(max_requests=10, window_seconds=60))])
    """

    def __init__(
        self,
        max_requests: int | None = None,
        window_seconds: int | None = None,
    ):
        self.max_requests = max_requests or settings.RATE_LIMIT_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS

    async def __call__(self, request: Request):
        redis = get_redis()
        if redis is None:
            return  # Skip rate limiting when Redis is unavailable

        # Key based on client IP + route
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{client_ip}:{request.url.path}"

        # Lua script for atomic sliding-window check
        lua_script = """
        local key = KEYS[1]
        local window = tonumber(ARGV[1])
        local max_requests = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        -- Remove old entries outside the window
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window * 1000)

        -- Count current requests in window
        local current = redis.call('ZCARD', key)

        if current >= max_requests then
            return -1
        end

        -- Add current request
        redis.call('ZADD', key, now, now .. '-' .. math.random(1000000))
        redis.call('EXPIRE', key, window)

        return max_requests - current - 1
        """

        import time
        now_ms = int(time.time() * 1000)

        try:
            remaining = await redis.eval(
                lua_script, 1, key, self.window_seconds, self.max_requests, now_ms
            )
        except Exception:
            # Redis connection lost at request time — skip rate limiting
            return

        if remaining < 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds}s.",
                headers={
                    "Retry-After": str(self.window_seconds),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )
