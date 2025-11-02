import pytest

from src.shortener import URLShortener
from src.storage import RedisStorage


class TestURLShortener:
    """Test URL shortener core logic."""

    @pytest.fixture
    async def shortener_instance(self, test_storage):
        """Provide URLShortener instance."""
        return URLShortener()

    async def test_generate_short_code(self, shortener_instance):
        """Test short code generation."""
        url = "https://example.com"
        timestamp = 1234567890
        code = shortener_instance.generate_short_code(url, timestamp)
        assert len(code) >= 7
        assert code.isalnum()

    async def test_generate_deterministic_code(self, shortener_instance):
        """Test that same input generates same code."""
        url = "https://example.com"
        timestamp = 1234567890
        code1 = shortener_instance.generate_short_code(url, timestamp)
        code2 = shortener_instance.generate_short_code(url, timestamp)
        assert code1 == code2

    async def test_generate_different_codes(self, shortener_instance):
        """Test that different inputs generate different codes."""
        url = "https://example.com"
        code1 = shortener_instance.generate_short_code(url, 1234567890)
        code2 = shortener_instance.generate_short_code(url, 1234567891)
        assert code1 != code2

    async def test_create_short_url(self, shortener_instance, test_storage):
        """Test creating a short URL."""
        url = "https://example.com/test"
        short_code, created_at = await shortener_instance.create_short_url(url)
        assert short_code
        assert created_at
        assert await test_storage.exists(short_code)

    async def test_create_with_custom_code(self, shortener_instance, test_storage):
        """Test creating URL with custom code."""
        url = "https://example.com/test"
        custom_code = "mycustom"
        short_code, _ = await shortener_instance.create_short_url(url, custom_code=custom_code)
        assert short_code == custom_code

    async def test_custom_code_collision(self, shortener_instance, test_storage):
        """Test that duplicate custom codes raise error."""
        url = "https://example.com/test"
        custom_code = "duplicate"
        await shortener_instance.create_short_url(url, custom_code=custom_code)

        with pytest.raises(ValueError, match="already exists"):
            await shortener_instance.create_short_url(url, custom_code=custom_code)

    async def test_get_original_url(self, shortener_instance, test_storage):
        """Test retrieving original URL."""
        url = "https://example.com/test"
        short_code, _ = await shortener_instance.create_short_url(url)
        retrieved_url = await shortener_instance.get_original_url(short_code)
        assert retrieved_url == url

    async def test_get_nonexistent_url(self, shortener_instance):
        """Test retrieving non-existent URL."""
        url = await shortener_instance.get_original_url("nonexistent")
        assert url is None

    async def test_delete_url(self, shortener_instance, test_storage):
        """Test deleting URL."""
        url = "https://example.com/test"
        short_code, _ = await shortener_instance.create_short_url(url)
        success = await shortener_instance.delete_url(short_code)
        assert success
        assert not await test_storage.exists(short_code)
