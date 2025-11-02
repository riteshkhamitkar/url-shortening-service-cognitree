import hashlib
import logging
from datetime import datetime, timezone

from hashids import Hashids

from src.config import settings
from src.storage import storage

logger = logging.getLogger(__name__)

# Initialize Hashids for generating short codes
hashids = Hashids(min_length=settings.short_code_length, alphabet="abcdefghijklmnopqrstuvwxyz0123456789")


class URLShortener:
    """Core URL shortening logic."""

    @staticmethod
    def generate_short_code(url: str, timestamp: int) -> str:
        """Generate deterministic short code from URL and timestamp."""
        # Create hash from URL + timestamp for uniqueness
        hash_input = f"{url}{timestamp}".encode()
        hash_digest = hashlib.sha256(hash_input).digest()
        # Convert first 8 bytes to integer for Hashids
        hash_int = int.from_bytes(hash_digest[:8], byteorder="big")
        return hashids.encode(hash_int)

    async def create_short_url(
        self, url: str, custom_code: str | None = None, ttl: int | None = None
    ) -> tuple[str, str]:
        """
        Create shortened URL.

        Returns:
            Tuple of (short_code, created_at timestamp)
        """
        ttl = ttl or settings.url_ttl_seconds
        timestamp = int(datetime.now(timezone.utc).timestamp())

        if custom_code:
            # Validate custom code availability
            if await storage.exists(custom_code):
                raise ValueError(f"Custom code '{custom_code}' already exists")
            short_code = custom_code
        else:
            # Generate unique short code
            attempts = 0
            while attempts < 5:
                short_code = self.generate_short_code(url, timestamp + attempts)
                if not await storage.exists(short_code):
                    break
                attempts += 1
            else:
                raise RuntimeError("Failed to generate unique short code")

        # Save to storage
        success = await storage.save_url(short_code, url, ttl)
        if not success:
            raise RuntimeError("Failed to save URL mapping")

        created_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        return short_code, created_at

    async def get_original_url(self, short_code: str) -> str | None:
        """Retrieve original URL by short code."""
        return await storage.get_url(short_code)

    async def get_stats(self, short_code: str) -> dict | None:
        """Get URL statistics."""
        return await storage.get_stats(short_code)

    async def delete_url(self, short_code: str) -> bool:
        """Delete shortened URL."""
        return await storage.delete_url(short_code)


# Global shortener instance
shortener = URLShortener()
