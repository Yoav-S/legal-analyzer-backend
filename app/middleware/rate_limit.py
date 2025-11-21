"""
Rate limiting middleware.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict, Tuple

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using in-memory storage."""
    
    def __init__(self, app):
        super().__init__(app)
        # In-memory storage: {ip: [(timestamp, endpoint), ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60  # Clean up old entries every 60 seconds
        self.last_cleanup = time.time()
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Clean up old entries periodically
        current_time = time.time()
        if current_time - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries(current_time)
            self.last_cleanup = current_time
        
        # Check rate limits
        endpoint = request.url.path
        
        # Per-minute limit
        if not self._check_limit(client_ip, endpoint, current_time, 60, settings.RATE_LIMIT_PER_MINUTE):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_MINUTE} requests per minute.",
                },
                headers={"Retry-After": "60"},
            )
        
        # Per-hour limit
        if not self._check_limit(client_ip, endpoint, current_time, 3600, settings.RATE_LIMIT_PER_HOUR):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Maximum {settings.RATE_LIMIT_PER_HOUR} requests per hour.",
                },
                headers={"Retry-After": "3600"},
            )
        
        # Record request
        self.requests[client_ip].append((current_time, endpoint))
        
        # Process request
        response = await call_next(request)
        return response
    
    def _check_limit(self, client_ip: str, endpoint: str, current_time: float, window: int, limit: int) -> bool:
        """Check if request is within rate limit."""
        window_start = current_time - window
        
        # Filter requests within window
        recent_requests = [
            ts for ts, ep in self.requests[client_ip]
            if ts > window_start
        ]
        
        return len(recent_requests) < limit
    
    def _cleanup_old_entries(self, current_time: float):
        """Remove entries older than 1 hour."""
        cutoff = current_time - 3600
        
        for ip in list(self.requests.keys()):
            self.requests[ip] = [
                (ts, ep) for ts, ep in self.requests[ip]
                if ts > cutoff
            ]
            
            # Remove empty entries
            if not self.requests[ip]:
                del self.requests[ip]

