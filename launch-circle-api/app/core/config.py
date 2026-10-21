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
    google_play_package_name: str = "com.launchcircle.testers"
    google_play_service_account_json: str = ""
    # The publisher account that owns Launch Circle's customer apps. Keep this
    # server-side; a client-supplied developer ID is only a claim until the
    # package can be verified with this account's Android Publisher access.
    google_play_developer_account_id: str = ""
    # Publisher IDs that can register any package owned by that verified Play
    # publisher without the per-additional-app purchase. Keep this allowlist
    # server-side; package ownership is still checked against the Publisher API.
    google_play_unlimited_developer_account_ids: str = ""
    google_play_additional_app_product_id: str = "additional_app_1"
    google_play_managed_product_id: str = "managed_launch_15"
    google_play_managed_credit_product_id: str = "managed_launch_14"
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
    cold_start_evidence_enabled: bool = False
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

    @property
    def unlimited_play_developer_account_ids(self) -> frozenset[str]:
        return frozenset(
            value.strip()
            for value in self.google_play_unlimited_developer_account_ids.split(",")
            if value.strip()
        )

    def has_unlimited_play_developer_account(self, account_id: str | None) -> bool:
        return bool(account_id and account_id.strip() in self.unlimited_play_developer_account_ids)

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
        if not self.google_play_developer_account_id.isdigit():
            raise ValueError(
                "GOOGLE_PLAY_DEVELOPER_ACCOUNT_ID must identify the verified publisher account"
            )
        if any(
            not account_id.isdigit()
            for account_id in self.unlimited_play_developer_account_ids
        ):
            raise ValueError(
                "GOOGLE_PLAY_UNLIMITED_DEVELOPER_ACCOUNT_IDS must contain numeric publisher IDs"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
