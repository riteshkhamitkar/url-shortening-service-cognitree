import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiting middleware."""

    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.cleanup_interval = 300  # Cleanup every 5 minutes
        self.last_cleanup = time.time()

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        client_ip = request.client.host
        now = datetime.now()

        # Periodic cleanup of old entries
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_entries()

        # Get request timestamps for this client
        timestamps = self.requests[client_ip]

        # Remove timestamps outside the window
        cutoff = now - timedelta(seconds=settings.rate_limit_window)
        timestamps[:] = [ts for ts in timestamps if ts > cutoff]

        # Check rate limit
        if len(timestamps) >= settings.rate_limit_requests:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(settings.rate_limit_window)},
            )

        # Add current request
        timestamps.append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            settings.rate_limit_requests - len(timestamps)
        )
        response.headers["X-RateLimit-Reset"] = str(
            int((now + timedelta(seconds=settings.rate_limit_window)).timestamp())
        )

        return response

    def _cleanup_old_entries(self):
        """Remove entries for IPs with no recent requests."""
        cutoff = datetime.now() - timedelta(seconds=settings.rate_limit_window * 2)
        to_remove = [
            ip for ip, timestamps in self.requests.items() if not timestamps or timestamps[-1] < cutoff
        ]
        for ip in to_remove:
            del self.requests[ip]
        self.last_cleanup = time.time()
        logger.debug(f"Cleaned up {len(to_remove)} rate limit entries")
