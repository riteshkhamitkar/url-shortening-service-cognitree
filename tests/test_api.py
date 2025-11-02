import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Test health check endpoint."""

    async def test_health_check(self, client: AsyncClient):
        """Test health endpoint returns correct status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "redis" in data
        assert "uptime" in data


class TestURLShortening:
    """Test URL shortening functionality."""

    async def test_create_short_url(self, client: AsyncClient, sample_url_data):
        """Test creating a shortened URL."""
        response = await client.post("/api/v1/shorten", json=sample_url_data)
        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert data["original_url"] == sample_url_data["url"]
        assert "created_at" in data
        assert "expires_at" in data

    async def test_create_with_custom_code(self, client: AsyncClient, sample_url):
        """Test creating URL with custom short code."""
        custom_code = "custom123"
        response = await client.post(
            "/api/v1/shorten", json={"url": sample_url, "custom_code": custom_code}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["short_code"] == custom_code

    async def test_create_with_custom_ttl(self, client: AsyncClient, sample_url):
        """Test creating URL with custom TTL."""
        ttl = 3600  # 1 hour
        response = await client.post("/api/v1/shorten", json={"url": sample_url, "ttl": ttl})
        assert response.status_code == 201
        data = response.json()
        assert "expires_at" in data

    async def test_duplicate_custom_code(self, client: AsyncClient, sample_url):
        """Test that duplicate custom codes are rejected."""
        custom_code = "duplicate"
        await client.post("/api/v1/shorten", json={"url": sample_url, "custom_code": custom_code})
        response = await client.post(
            "/api/v1/shorten", json={"url": sample_url, "custom_code": custom_code}
        )
        assert response.status_code == 400

    async def test_invalid_url(self, client: AsyncClient):
        """Test that invalid URLs are rejected."""
        response = await client.post("/api/v1/shorten", json={"url": "not-a-valid-url"})
        assert response.status_code == 422

    async def test_invalid_custom_code(self, client: AsyncClient, sample_url):
        """Test that invalid custom codes are rejected."""
        response = await client.post(
            "/api/v1/shorten", json={"url": sample_url, "custom_code": "ab"}  # Too short
        )
        assert response.status_code == 422

        response = await client.post(
            "/api/v1/shorten",
            json={"url": sample_url, "custom_code": "invalid@code"},  # Invalid chars
        )
        assert response.status_code == 422


class TestURLRedirection:
    """Test URL redirection functionality."""

    async def test_redirect_to_original_url(self, client: AsyncClient, sample_url):
        """Test redirecting to original URL."""
        # Create short URL
        create_response = await client.post("/api/v1/shorten", json={"url": sample_url})
        short_code = create_response.json()["short_code"]

        # Test redirect
        response = await client.get(f"/{short_code}", follow_redirects=False)
        assert response.status_code == 301
        assert response.headers["location"] == sample_url

    async def test_redirect_nonexistent_code(self, client: AsyncClient):
        """Test redirecting with non-existent short code."""
        response = await client.get("/nonexistent", follow_redirects=False)
        assert response.status_code == 404

    async def test_invalid_short_code_format(self, client: AsyncClient):
        """Test redirect with invalid short code format."""
        response = await client.get("/ab", follow_redirects=False)  # Too short
        assert response.status_code == 400


class TestURLStats:
    """Test URL statistics functionality."""

    async def test_get_stats(self, client: AsyncClient, sample_url):
        """Test retrieving URL statistics."""
        # Create short URL
        create_response = await client.post("/api/v1/shorten", json={"url": sample_url})
        short_code = create_response.json()["short_code"]

        # Get stats
        response = await client.get(f"/api/v1/stats/{short_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == short_code
        assert data["original_url"] == sample_url
        assert data["clicks"] == 0
        assert "created_at" in data

    async def test_stats_increment_clicks(self, client: AsyncClient, sample_url):
        """Test that clicks are incremented on redirect."""
        # Create short URL
        create_response = await client.post("/api/v1/shorten", json={"url": sample_url})
        short_code = create_response.json()["short_code"]

        # Redirect multiple times
        await client.get(f"/{short_code}", follow_redirects=False)
        await client.get(f"/{short_code}", follow_redirects=False)

        # Check stats
        response = await client.get(f"/api/v1/stats/{short_code}")
        data = response.json()
        assert data["clicks"] == 2

    async def test_stats_nonexistent_code(self, client: AsyncClient):
        """Test stats for non-existent short code."""
        response = await client.get("/api/v1/stats/nonexistent")
        assert response.status_code == 404


class TestURLDeletion:
    """Test URL deletion functionality."""

    async def test_delete_url(self, client: AsyncClient, sample_url):
        """Test deleting a shortened URL."""
        # Create short URL
        create_response = await client.post("/api/v1/shorten", json={"url": sample_url})
        short_code = create_response.json()["short_code"]

        # Delete URL
        response = await client.delete(f"/api/v1/urls/{short_code}")
        assert response.status_code == 204

        # Verify deletion
        response = await client.get(f"/{short_code}", follow_redirects=False)
        assert response.status_code == 404

    async def test_delete_nonexistent_url(self, client: AsyncClient):
        """Test deleting non-existent URL."""
        response = await client.delete("/api/v1/urls/nonexistent")
        assert response.status_code == 404
