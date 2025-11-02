import pytest


class TestRedisStorage:
    """Test Redis storage operations."""

    async def test_save_and_get_url(self, test_storage):
        """Test saving and retrieving URL."""
        short_code = "test123"
        url = "https://example.com"
        ttl = 3600

        success = await test_storage.save_url(short_code, url, ttl)
        assert success

        retrieved_url = await test_storage.get_url(short_code)
        assert retrieved_url == url

    async def test_url_exists(self, test_storage):
        """Test checking URL existence."""
        short_code = "exists123"
        url = "https://example.com"
        ttl = 3600

        assert not await test_storage.exists(short_code)

        await test_storage.save_url(short_code, url, ttl)
        assert await test_storage.exists(short_code)

    async def test_get_stats(self, test_storage):
        """Test retrieving URL statistics."""
        short_code = "stats123"
        url = "https://example.com"
        ttl = 3600

        await test_storage.save_url(short_code, url, ttl)
        stats = await test_storage.get_stats(short_code)

        assert stats is not None
        assert stats["original_url"] == url
        assert stats["clicks"] == 0
        assert "created_at" in stats

    async def test_increment_clicks(self, test_storage):
        """Test click counter increment."""
        short_code = "clicks123"
        url = "https://example.com"
        ttl = 3600

        await test_storage.save_url(short_code, url, ttl)

        # Simulate multiple accesses
        await test_storage.get_url(short_code)
        await test_storage.get_url(short_code)
        await test_storage.get_url(short_code)

        stats = await test_storage.get_stats(short_code)
        assert stats["clicks"] == 3

    async def test_delete_url(self, test_storage):
        """Test deleting URL."""
        short_code = "delete123"
        url = "https://example.com"
        ttl = 3600

        await test_storage.save_url(short_code, url, ttl)
        assert await test_storage.exists(short_code)

        success = await test_storage.delete_url(short_code)
        assert success
        assert not await test_storage.exists(short_code)

    async def test_get_nonexistent_stats(self, test_storage):
        """Test getting stats for non-existent URL."""
        stats = await test_storage.get_stats("nonexistent")
        assert stats is None

    async def test_health_check(self, test_storage):
        """Test Redis health check."""
        healthy = await test_storage.health_check()
        assert healthy is True
