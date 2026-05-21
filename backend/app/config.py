import ssl

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://brightsolar:brightsolar@db:5432/brightsolar"
    cors_origins: str = "http://localhost:3000"
    cors_origin_regex: str | None = None
    env: str = "development"
    jwt_secret: str = "change-me-in-production-this-is-a-dev-only-default"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def sqlalchemy_connect_args(self) -> dict[str, object]:
        if self.env == "production" and "localhost" not in self.sqlalchemy_database_url:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return {"ssl": ssl_context}
        return {}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_cors_origin_regex(self) -> str | None:
        if self.env == "production":
            return None
        return self.cors_origin_regex


settings = Settings()
