"""Typed public contracts for the native CBRA HTTP boundary."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import (
    BaseModel,
    Field,
    StrictBool,
    StrictInt,
    StrictStr,
)

try:
    from pydantic import ConfigDict
except ImportError:  # Pydantic 1
    ConfigDict = None

try:
    from pydantic import field_validator
except ImportError:  # Pydantic 1
    field_validator = None
    from pydantic import validator

from cbra.application import (
    ApplicationSessionSummary,
    ApplicationTurnResult,
)
from cbra.native import TurnOutcomeKind


if hasattr(BaseModel, "model_validate"):

    class PublicModel(BaseModel):
        """Closed public schema for requests and responses."""

        model_config = ConfigDict(extra="forbid")

else:

    class PublicModel(BaseModel):
        """Closed public schema for requests and responses."""

        class Config:
            extra = "forbid"


class TurnRequest(PublicModel):
    user_text: StrictStr = Field(..., min_length=1)
    turn_id: Optional[StrictStr] = Field(default=None, min_length=1)
    expected_revision: Optional[StrictInt] = None
    mode: Literal["production", "debug"] = "production"

    if field_validator is not None:

        @field_validator("user_text")
        @classmethod
        def user_text_has_material(cls, value):
            if not value.strip():
                raise ValueError("user_text must contain non-whitespace")
            return value

        @field_validator("turn_id")
        @classmethod
        def turn_id_has_material(cls, value):
            if value is not None and not value.strip():
                raise ValueError("turn_id must contain non-whitespace")
            return value

        @field_validator("expected_revision")
        @classmethod
        def revision_is_non_negative(cls, value):
            if value is not None and value < 0:
                raise ValueError(
                    "expected_revision must be non-negative"
                )
            return value

    else:

        @validator("user_text")
        def user_text_has_material(cls, value):
            if not value.strip():
                raise ValueError("user_text must contain non-whitespace")
            return value

        @validator("turn_id")
        def turn_id_has_material(cls, value):
            if value is not None and not value.strip():
                raise ValueError("turn_id must contain non-whitespace")
            return value

        @validator("expected_revision")
        def revision_is_non_negative(cls, value):
            if value is not None and value < 0:
                raise ValueError(
                    "expected_revision must be non-negative"
                )
            return value


class TurnDebug(PublicModel):
    cycle_start: StrictInt
    cycle_end: StrictInt
    cycles_run: StrictInt
    reintegration_count: StrictInt
    idempotent_replay: StrictBool


class TurnResponse(PublicModel):
    request_id: StrictStr
    thread_id: StrictStr
    turn_id: StrictStr
    revision: StrictInt
    outcome: TurnOutcomeKind
    text: Optional[StrictStr]
    debug: Optional[TurnDebug] = None

    @classmethod
    def from_result(
        cls,
        request_id: str,
        result: ApplicationTurnResult,
        *,
        include_debug: bool,
    ) -> "TurnResponse":
        outcome = result.outcome
        debug = None
        if include_debug:
            debug = TurnDebug(
                cycle_start=outcome.cycle_start,
                cycle_end=outcome.cycle_end,
                cycles_run=outcome.cycle_end - outcome.cycle_start + 1,
                reintegration_count=len(outcome.reintegrations),
                idempotent_replay=result.replayed,
            )
        return cls(
            request_id=request_id,
            thread_id=outcome.thread_id,
            turn_id=outcome.turn_id,
            revision=outcome.revision,
            outcome=outcome.kind,
            text=outcome.text,
            debug=debug,
        )


class SessionSummaryResponse(PublicModel):
    request_id: StrictStr
    thread_id: StrictStr
    revision: StrictInt
    turn_count: StrictInt
    latest_outcome: Optional[TurnOutcomeKind]
    reintegration_pending: StrictBool

    @classmethod
    def from_summary(
        cls,
        request_id: str,
        summary: ApplicationSessionSummary,
    ) -> "SessionSummaryResponse":
        return cls(
            request_id=request_id,
            thread_id=summary.thread_id,
            revision=summary.revision,
            turn_count=summary.turn_count,
            latest_outcome=summary.latest_outcome,
            reintegration_pending=summary.reintegration_pending,
        )


class HealthResponse(PublicModel):
    ok: StrictBool
    app: StrictStr
    version: StrictStr
    persistence: Literal["native_session_repository"]


class ErrorDetail(PublicModel):
    code: StrictStr
    message: StrictStr
    fields: Optional[List[StrictStr]] = None


class ErrorResponse(PublicModel):
    request_id: StrictStr
    error: ErrorDetail
