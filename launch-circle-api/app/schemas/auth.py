from pydantic import BaseModel, Field, field_validator


class GoogleAuthRequest(BaseModel):
    id_token: str
    acquisition_source: str | None = Field(default=None, max_length=120)
    acquisition_medium: str | None = Field(default=None, max_length=120)
    acquisition_campaign: str | None = Field(default=None, max_length=120)

    @field_validator("acquisition_source", "acquisition_medium", "acquisition_campaign")
    @classmethod
    def normalize_attribution(cls, value: str | None) -> str | None:
        return value.strip()[:120] if value and value.strip() else None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
