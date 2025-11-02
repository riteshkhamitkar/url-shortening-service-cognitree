import logging
import time

from src.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory counters (for basic metrics)
url_created_counter = {"count": 0}
url_redirected_counter = {"count": 0}
url_not_found_counter = {"count": 0}


def setup_logging():
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_telemetry(app):
    """Placeholder for telemetry setup."""
    logger.info("Telemetry setup skipped (minimal version)")


async def metrics_endpoint():
    """Simple metrics endpoint."""
    metrics = f"""# URL Shortener Metrics
url_created_total {url_created_counter['count']}
url_redirected_total {url_redirected_counter['count']}
url_not_found_total {url_not_found_counter['count']}
"""
    from fastapi import Response
    return Response(content=metrics, media_type="text/plain")
