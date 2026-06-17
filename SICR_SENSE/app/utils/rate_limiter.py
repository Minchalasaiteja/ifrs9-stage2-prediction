import time
import asyncio
from typing import Dict, Tuple, Optional
from fastapi import HTTPException, Request, status
import redis.asyncio as redis
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connection established for rate limiting")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory rate limiting: {e}")
            self.redis_client = None
    
    async def is_rate_limited(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, Dict]:
        """Check if request should be rate limited"""
        current_time = time.time()
        window_start = current_time - window_seconds
        
        if self.redis_client:
            # Redis-based rate limiting (sliding window)
            pipeline = self.redis_client.pipeline()
            pipeline.zremrangebyscore(key, 0, window_start)
            pipeline.zcard(key)
            pipeline.zadd(key, {str(current_time): current_time})
            pipeline.expire(key, window_seconds)
            results = await pipeline.execute()
            
            request_count = results[1]
        else:
            # Simple in-memory fallback
            if not hasattr(self, '_memory_store'):
                self._memory_store = {}
            
            if key not in self._memory_store:
                self._memory_store[key] = []
            
            # Clean old entries
            self._memory_store[key] = [
                ts for ts in self._memory_store[key] 
                if ts > window_start
            ]
            self._memory_store[key].append(current_time)
            request_count = len(self._memory_store[key])
        
        remaining = max(0, max_requests - request_count)
        reset_time = current_time + window_seconds
        
        return request_count > max_requests, {
            "limit": max_requests,
            "remaining": remaining,
            "reset": reset_time
        }

# Initialize rate limiter
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """FastAPI middleware for rate limiting"""
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host
        user_id = request.state.user_id if hasattr(request.state, 'user_id') else client_ip
        
        # Different limits for different endpoints
        if "predict" in request.url.path:
            limits = (100, 60)  # 100 requests per minute
        elif "auth" in request.url.path:
            limits = (20, 300)  # 20 requests per 5 minutes
        else:
            limits = (1000, 60)  # Default: 1000 requests per minute
        
        is_limited, rate_info = await rate_limiter.is_rate_limited(
            f"rate_limit:{user_id}:{request.url.path}",
            limits[0],
            limits[1]
        )
        
        if is_limited:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset"])
                }
            )
    
    response = await call_next(request)
    return response