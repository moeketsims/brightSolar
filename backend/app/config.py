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
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def effective_cors_origin_regex(self) -> str | None:
        if self.env == "production":
            return None
        return self.cors_origin_regex


settings = Settings()
