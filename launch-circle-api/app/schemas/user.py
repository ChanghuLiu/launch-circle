from pydantic import BaseModel, EmailStr, Field, field_validator


ALLOWED_CAPABILITIES = {"BLUETOOTH", "NFC", "ESIM", "CAMERA", "GPS", "OTHER"}


class UserRead(BaseModel):
    id: str
    login_email: EmailStr
    display_name: str | None
    tester_email: EmailStr | None
    tester_email_sharing_consent: bool
    country: str | None
    languages: list[str]
    profile_ready: bool


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    languages: list[str] | None = None

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value else None

    @field_validator("languages")
    @classmethod
    def normalize_languages(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = sorted({item.strip().lower() for item in value if item.strip()})
        if len(cleaned) > 10:
            raise ValueError("at most 10 languages are allowed")
        return cleaned


class TesterEmailUpdate(BaseModel):
    tester_email: EmailStr
    sharing_consent: bool


class DeviceUpdate(BaseModel):
    installation_id: str = Field(min_length=8, max_length=100)
    manufacturer: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    android_api: int = Field(ge=26, le=100)
    capabilities: list[str] = Field(default_factory=list)

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        normalized = sorted({item.upper() for item in value})
        invalid = set(normalized) - ALLOWED_CAPABILITIES
        if invalid:
            raise ValueError(f"unsupported capabilities: {sorted(invalid)}")
        return normalized
