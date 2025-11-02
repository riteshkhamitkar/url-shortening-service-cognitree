from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration with environment variable support."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Application
    app_name: str = "url-shortener"
    app_version: str = "1.0.0"
    environment: str = "production"
    log_level: str = "INFO"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""
    redis_max_connections: int = 50
    redis_socket_keepalive: bool = True
    redis_socket_connect_timeout: int = 5
    redis_health_check_interval: int = 30

    # URL Configuration
    base_url: str = "http://localhost:8000"
    short_code_length: int = 7
    url_ttl_seconds: int = 2592000  # 30 days

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    # OpenTelemetry
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "url-shortener"

    # Metrics
    metrics_enabled: bool = True
    metrics_port: int = 9090

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


settings = Settings()
