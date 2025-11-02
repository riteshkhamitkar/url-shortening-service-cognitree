import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from src.config import settings

logger = logging.getLogger(__name__)


class RedisStorage:
    """Redis-based storage for URL mappings with connection pooling."""

    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connection pool."""
        self.pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
        self.client = redis.Redis(connection_pool=self.pool)
        logger.info("Redis connection pool initialized")

    async def disconnect(self):
        """Close Redis connection pool."""
        if self.client:
            await self.client.aclose()
        if self.pool:
            await self.pool.aclose()
        logger.info("Redis connection pool closed")

    async def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def save_url(self, short_code: str, url: str, ttl: int) -> bool:
        """Save URL mapping with TTL."""
        try:
            pipe = self.client.pipeline()
            timestamp = datetime.now(timezone.utc).isoformat()

            # Store URL mapping
            pipe.setex(f"url:{short_code}", ttl, url)
            # Store metadata
            pipe.hset(
                f"meta:{short_code}",
                mapping={"created_at": timestamp, "clicks": 0, "url": url},
            )
            pipe.expire(f"meta:{short_code}", ttl)

            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Failed to save URL {short_code}: {e}")
            return False

    async def get_url(self, short_code: str) -> Optional[str]:
        """Retrieve original URL and increment click counter."""
        try:
            pipe = self.client.pipeline()
            pipe.get(f"url:{short_code}")
            pipe.hincrby(f"meta:{short_code}", "clicks", 1)
            results = await pipe.execute()
            return results[0]
        except Exception as e:
            logger.error(f"Failed to get URL {short_code}: {e}")
            return None

    async def get_stats(self, short_code: str) -> Optional[dict]:
        """Get URL statistics."""
        try:
            pipe = self.client.pipeline()
            pipe.hgetall(f"meta:{short_code}")
            pipe.ttl(f"url:{short_code}")
            results = await pipe.execute()

            meta = results[0]
            ttl = results[1]

            if not meta:
                return None

            expires_at = None
            if ttl > 0:
                from datetime import timedelta

                created = datetime.fromisoformat(meta["created_at"])
                expires_at = (created + timedelta(seconds=ttl)).isoformat()

            return {
                "original_url": meta["url"],
                "clicks": int(meta.get("clicks", 0)),
                "created_at": meta["created_at"],
                "expires_at": expires_at,
            }
        except Exception as e:
            logger.error(f"Failed to get stats {short_code}: {e}")
            return None

    async def exists(self, short_code: str) -> bool:
        """Check if short code exists."""
        try:
            return await self.client.exists(f"url:{short_code}") > 0
        except Exception as e:
            logger.error(f"Failed to check existence {short_code}: {e}")
            return False

    async def delete_url(self, short_code: str) -> bool:
        """Delete URL mapping."""
        try:
            # Check if URL exists first
            if not await self.exists(short_code):
                return False
            
            pipe = self.client.pipeline()
            pipe.delete(f"url:{short_code}")
            pipe.delete(f"meta:{short_code}")
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete URL {short_code}: {e}")
            return False


# Global storage instance
storage = RedisStorage()
