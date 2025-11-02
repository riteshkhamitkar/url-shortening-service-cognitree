import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse

from src.config import settings
from src.models import URLCreate, URLResponse, URLStats, HealthResponse
from src.shortener import shortener
from src.storage import storage
from src.middleware import RateLimitMiddleware
from src.observability import (
    setup_logging,
    setup_telemetry,
    metrics_endpoint,
    url_created_counter,
    url_redirected_counter,
    url_not_found_counter,
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Application startup time
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    await storage.connect()
    yield
    logger.info("Shutting down application")
    await storage.disconnect()


# Initialize FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Add middleware
app.add_middleware(RateLimitMiddleware)

# Setup telemetry
setup_telemetry(app)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for load balancers and orchestrators."""
    redis_status = "healthy" if await storage.health_check() else "unhealthy"
    uptime = time.time() - START_TIME

    return HealthResponse(
        status="healthy" if redis_status == "healthy" else "degraded",
        version=settings.app_version,
        redis=redis_status,
        uptime=uptime,
    )


@app.get("/metrics", tags=["Observability"])
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    return await metrics_endpoint()


@app.post("/api/v1/shorten", response_model=URLResponse, status_code=status.HTTP_201_CREATED, tags=["URL"])
async def create_short_url(request: URLCreate):
    """
    Create a shortened URL.

    - **url**: Original URL to shorten (required)
    - **custom_code**: Custom short code (optional, 4-20 alphanumeric characters)
    - **ttl**: Time-to-live in seconds (optional, max 1 year, default 30 days)
    """
    try:
        short_code, created_at = await shortener.create_short_url(
            url=str(request.url), custom_code=request.custom_code, ttl=request.ttl
        )

        url_created_counter["count"] += 1

        # Calculate expiration
        ttl = request.ttl or settings.url_ttl_seconds
        expires_at = (
            datetime.fromisoformat(created_at) + timedelta(seconds=ttl)
        ).isoformat()

        return URLResponse(
            short_code=short_code,
            short_url=f"{settings.base_url}/{short_code}",
            original_url=str(request.url),
            created_at=created_at,
            expires_at=expires_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create short URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create short URL",
        )


@app.get("/{short_code}", tags=["URL"])
async def redirect_to_url(short_code: str):
    """
    Redirect to original URL using short code.

    This endpoint increments the click counter and redirects to the original URL.
    """
    if len(short_code) < 4 or len(short_code) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid short code")

    url = await shortener.get_original_url(short_code)

    if not url:
        url_not_found_counter["count"] += 1
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    url_redirected_counter["count"] += 1
    return RedirectResponse(url=url, status_code=status.HTTP_301_MOVED_PERMANENTLY)


@app.get("/api/v1/stats/{short_code}", response_model=URLStats, tags=["URL"])
async def get_url_stats(short_code: str):
    """
    Get statistics for a shortened URL.

    Returns click count, creation time, and expiration time.
    """
    stats = await shortener.get_stats(short_code)

    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    return URLStats(short_code=short_code, **stats)


@app.delete("/api/v1/urls/{short_code}", status_code=status.HTTP_204_NO_CONTENT, tags=["URL"])
async def delete_url(short_code: str):
    """
    Delete a shortened URL.

    This permanently removes the URL mapping and all associated metadata.
    """
    success = await shortener.delete_url(short_code)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="URL not found or already deleted"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
