from pydantic import BaseModel, HttpUrl, Field, field_validator


class URLCreate(BaseModel):
    """Request model for creating shortened URL."""

    url: HttpUrl = Field(..., description="Original URL to shorten")
    custom_code: str | None = Field(None, min_length=4, max_length=20, pattern="^[a-zA-Z0-9_-]+$")
    ttl: int | None = Field(None, gt=0, le=31536000, description="TTL in seconds (max 1 year)")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> str:
        """Convert HttpUrl to string and validate."""
        url_str = str(v)
        if len(url_str) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        return url_str


class URLResponse(BaseModel):
    """Response model for shortened URL."""

    short_code: str = Field(..., description="Generated short code")
    short_url: str = Field(..., description="Complete shortened URL")
    original_url: str = Field(..., description="Original URL")
    created_at: str = Field(..., description="Creation timestamp")
    expires_at: str | None = Field(None, description="Expiration timestamp")


class URLStats(BaseModel):
    """Statistics for a shortened URL."""

    short_code: str
    original_url: str
    clicks: int = 0
    created_at: str
    expires_at: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    redis: str
    uptime: float
