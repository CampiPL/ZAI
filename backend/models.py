import re
from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr, field_validator, model_validator

Name = Annotated[str, Field(strict=True, min_length=1, max_length=100)]
Number = Annotated[StrictFloat, Field(allow_inf_nan=False)]


def timestamp(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value
    ):
        raise ValueError("Podaj czas ISO 8601 ze strefą, np. 2026-11-01T12:00:00Z.")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class Input(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Login(Input):
    username: Annotated[str, Field(strict=True, min_length=1, max_length=100)]
    password: Annotated[str, Field(strict=True, min_length=1, max_length=1024)]


class PasswordChange(Input):
    currentPassword: Annotated[str, Field(strict=True, max_length=1024)]
    newPassword: Annotated[str, Field(strict=True, min_length=8, max_length=1024)]


class SeriesInput(Input):
    name: Name
    minValue: Number
    maxValue: Number
    color: Annotated[str, Field(strict=True, pattern=r"^#[0-9A-Fa-f]{6}$")]
    icon: Annotated[str, Field(strict=True, max_length=100)] | None = None
    unit: Annotated[str, Field(strict=True, max_length=20)] | None = None

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Nazwa nie może być pusta.")
        return value.strip()

    @model_validator(mode="after")
    def ordered_range(self):
        if self.minValue >= self.maxValue:
            raise ValueError("Minimum musi być mniejsze od maksimum.")
        return self


class SensorInput(Input):
    name: Name
    seriesId: StrictInt | StrictStr

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Nazwa nie może być pusta.")
        return value.strip()


class MeasurementInput(Input):
    value: Number
    timestamp: StrictStr = Field(default_factory=now_iso)

    @field_validator("timestamp")
    @classmethod
    def valid_timestamp(cls, value):
        return timestamp(value)
