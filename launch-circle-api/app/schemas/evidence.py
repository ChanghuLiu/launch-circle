from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EnrollmentEvidenceCreate(StrictInput):
    event: Literal["JOINED", "LEFT", "UNKNOWN"]
    source: Literal["SELF_REPORTED", "OWNER_CONFIRMED"] = "SELF_REPORTED"
    note: str = Field(min_length=1, max_length=2000)


class EnrollmentEvidenceRead(EnrollmentEvidenceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    assignment_id: str
    recorded_at: datetime


class StepEvidence(StrictInput):
    instruction: str = Field(min_length=1, max_length=500)
    expected: str = Field(min_length=1, max_length=1000)
    actual: str = Field(min_length=1, max_length=2000)
    result: Literal["PASS", "FAIL", "BLOCKED", "NOT_RUN"]


class MissionRunCreate(StrictInput):
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    execution_source: Literal["HUMAN_MANUAL", "CODEX_ASSISTED", "AUTOMATED_RUNNER"]
    result: Literal["PASS", "FAIL", "BLOCKED", "NOT_RUN"]
    package_name: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9_.]+$")
    version_code: int = Field(gt=0)
    expected_version_code: int = Field(gt=0)
    device_key: str = Field(min_length=1, max_length=120)
    device_model: str = Field(min_length=1, max_length=120)
    android_api: int = Field(ge=1, le=100)
    steps: list[StepEvidence] = Field(min_length=1, max_length=20)
    note: str = Field(default="", max_length=2000)
    retest_of_id: str | None = Field(default=None, min_length=1, max_length=36)

    @model_validator(mode="after")
    def validate_outcome(self):
        results = {step.result for step in self.steps}
        if self.result == "PASS" and (
            results != {"PASS"} or self.version_code != self.expected_version_code
        ):
            raise ValueError("PASS requires the expected build and all recorded steps passing")
        if self.result == "FAIL" and "FAIL" not in results:
            raise ValueError("FAIL requires a failing step")
        if self.result == "BLOCKED" and "BLOCKED" not in results:
            raise ValueError("BLOCKED requires a blocked step")
        if self.result == "NOT_RUN" and results != {"NOT_RUN"}:
            raise ValueError("NOT_RUN requires all steps to be unexecuted")
        return self


class MissionRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    mission_id: str
    idempotency_key: str
    execution_source: str
    result: str
    package_name: str
    version_code: int
    device_key: str
    device_model: str
    android_api: int
    details: dict
    retest_of_id: str | None
    recorded_at: datetime


class MissionRunFixCreate(StrictInput):
    target_version_code: int = Field(gt=0)
    description: str = Field(min_length=1, max_length=2000)
