"""API contracts. Missing measurements are null, never manufactured zeroes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, FiniteFloat, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Health(Contract):
    status: Literal["ok"] = "ok"
    api_version: Literal["v1"] = "v1"
    data_ready: Literal[False] = False
    snapshot_id: str | None = None
    core_source_count: int | None = None
    reason: str


class ErrorDetail(Contract):
    code: Literal["not_ready", "not_found"]
    message: str


class ErrorResponse(Contract):
    detail: ErrorDetail


class RunIdentity(Contract):
    run_id: str
    data_version: str
    factor_version: str
    package_id: str
    scenario: Literal["low", "mid", "high"]
    horizon: Literal["annual_baseline", "first_year", "steady_state"]
    period_start: str
    period_end: str


class Measurement(Contract):
    value: FiniteFloat | None
    unit: Literal["CHF", "kWh", "kg_CO2", "kg_CO2e", "percent", "person_days"]
    estimated: bool
    quality_flags: list[str] = Field(min_length=1)


class Overview(Contract):
    context: RunIdentity
    cost: Measurement
    energy: Measurement
    emissions: Measurement
