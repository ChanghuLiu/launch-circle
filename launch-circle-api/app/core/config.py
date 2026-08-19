from functools import lru_cache
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEVELOPMENT_JWT_SECRET = "development-only-change-me"
DEPLOYMENT_ENVIRONMENTS = {"pilot", "production"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )

    app_env: str = "development"
    database_url: str = Field(
        default="sqlite:///./data/launch_circle.db",
        validation_alias="SQLITE_DATABASE_URL",
    )
    jwt_secret: str = Field(min_length=16, default=DEVELOPMENT_JWT_SECRET)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")
    public_base_url: str = Field(
        default="https://launchcircle.app",
        validation_alias="PUBLIC_BASE_URL",
    )
    google_client_id: str = ""
    invite_base_url: str = Field(
        default="https://launchcircle.app/join",
        validation_alias=AliasChoices("INVITE_BASE_URL", "LAUNCH_CIRCLE_INVITE_BASE_URL"),
    )
    google_group_email: str = Field(
        default="launch-circle-12-testers@googlegroups.com",
        validation_alias=AliasChoices("GOOGLE_GROUP_EMAIL", "LAUNCH_CIRCLE_GOOGLE_GROUP_EMAIL"),
    )
    google_group_url: str = Field(
        default="https://groups.google.com/g/launch-circle-12-testers",
        validation_alias=AliasChoices("GOOGLE_GROUP_URL", "LAUNCH_CIRCLE_GOOGLE_GROUP_JOIN_URL"),
    )
    development_auth_enabled: bool = True

    @property
    def is_deployment(self) -> bool:
        return self.app_env.lower() in DEPLOYMENT_ENVIRONMENTS

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def launch_circle_google_group_email(self) -> str:
        return self.google_group_email

    @property
    def launch_circle_google_group_join_url(self) -> str:
        return self.google_group_url

    @property
    def launch_circle_invite_base_url(self) -> str:
        return self.invite_base_url.rstrip(chr(47))

    @model_validator(mode="after")
    def validate_deployment_safety(self) -> "Settings":
        if not self.is_deployment:
            return self
        if self.jwt_secret == DEVELOPMENT_JWT_SECRET:
            raise ValueError("JWT_SECRET must be set to a unique secret for pilot/production")
        if self.development_auth_enabled:
            raise ValueError("DEVELOPMENT_AUTH_ENABLED must be false for pilot/production")
        if not self.database_url.startswith("sqlite:////"):
            raise ValueError(
                "SQLITE_DATABASE_URL must use an absolute SQLite path for pilot/production"
            )
        public_url = urlparse(self.public_base_url)
        if public_url.scheme != "https" or not public_url.netloc:
            raise ValueError("PUBLIC_BASE_URL must use HTTPS for pilot/production")
        if any(
            urlparse(origin).scheme != "https" or not urlparse(origin).netloc
            for origin in self.cors_origin_list
        ):
            raise ValueError("CORS_ORIGINS must contain only HTTPS origins for pilot/production")
        if "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS cannot contain * for pilot/production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
