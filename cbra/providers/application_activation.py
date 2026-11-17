"""Explicit application bootstrap for provider-owned articulation rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import os
import threading
from typing import Mapping, Optional

from cbra.native import (
    ArticulationRenderer,
    ArticulationRendererBinding,
)

from .openai_responses import (
    OpenAIResponsesArticulationRenderer,
    OpenAIResponsesRendererConfiguration,
)


NATIVE_TEMPLATE_RENDERER = "native-template"
OPENAI_RESPONSES_RENDERER = "openai-responses"
RENDERER_SELECTOR_ENVIRONMENT_VARIABLE = "CBRA_ARTICULATION_RENDERER"

_OPENAI_API_BASE_URL = "https://api.openai.com/v1"
_AMBIENT_OPENAI_OVERRIDES = (
    "OPENAI_BASE_URL",
    "OPENAI_LOG",
    "OPENAI_ORGANIZATION",
    "OPENAI_ORG_ID",
    "OPENAI_PROJECT",
    "OPENAI_PROJECT_ID",
)
_OPENAI_REQUIRED_ENVIRONMENT_VARIABLES = (
    "OPENAI_API_KEY",
    "CBRA_OPENAI_MODEL",
    "CBRA_OPENAI_REASONING_EFFORT",
    "CBRA_OPENAI_TEXT_VERBOSITY",
    "CBRA_OPENAI_MAX_INPUT_CHARS",
    "CBRA_OPENAI_MAX_OUTPUT_TOKENS",
    "CBRA_OPENAI_MAX_OUTPUT_CHARS",
    "CBRA_OPENAI_TIMEOUT_SECONDS",
)


class ApplicationRendererActivationError(RuntimeError):
    """Application rendering cannot be activated from process configuration."""


@dataclass
class _CloseState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    closed: bool = False


@dataclass(frozen=True)
class ApplicationRendererActivation:
    """One resolved renderer and the client resources it owns."""

    renderer: Optional[ArticulationRenderer] = None
    renderer_binding: Optional[ArticulationRendererBinding] = None
    _client: Optional[object] = field(
        default=None,
        repr=False,
        compare=False,
    )
    _close_state: _CloseState = field(
        default_factory=_CloseState,
        repr=False,
        compare=False,
    )

    def close(self) -> None:
        """Close an owned provider client at most once."""
        if self._client is None:
            return
        with self._close_state.lock:
            if self._close_state.closed:
                return
            self._close_state.closed = True
            close = getattr(self._client, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    raise ApplicationRendererActivationError(
                        "OpenAI client could not be closed"
                    ) from None


def _environment_value(
    environment: Mapping[str, str],
    name: str,
) -> Optional[str]:
    try:
        value = environment.get(name)
    except Exception:
        raise ApplicationRendererActivationError(
            "Application renderer environment could not be read"
        ) from None
    if value is not None and not isinstance(value, str):
        raise ApplicationRendererActivationError(
            "Application renderer environment contains a non-text value"
        )
    return value


def _required_environment_value(
    environment: Mapping[str, str],
    name: str,
) -> str:
    value = _environment_value(environment, name)
    if value is None or not value.strip():
        raise ApplicationRendererActivationError(
            "OpenAI renderer activation requires {0}".format(name)
        )
    return value


def _required_integer(
    environment: Mapping[str, str],
    name: str,
) -> int:
    value = _required_environment_value(environment, name)
    try:
        if value != value.strip():
            raise ValueError
        return int(value, 10)
    except (TypeError, ValueError, OverflowError):
        raise ApplicationRendererActivationError(
            "{0} must be a base-10 integer".format(name)
        ) from None


def _required_finite_number(
    environment: Mapping[str, str],
    name: str,
) -> float:
    value = _required_environment_value(environment, name)
    try:
        if value != value.strip():
            raise ValueError
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ApplicationRendererActivationError(
            "{0} must be a finite number".format(name)
        ) from None
    if not math.isfinite(number):
        raise ApplicationRendererActivationError(
            "{0} must be a finite number".format(name)
        )
    return number


def _configuration_from_environment(
    environment: Mapping[str, str],
) -> OpenAIResponsesRendererConfiguration:
    try:
        return OpenAIResponsesRendererConfiguration(
            model_id=_required_environment_value(
                environment,
                "CBRA_OPENAI_MODEL",
            ),
            reasoning_effort=_required_environment_value(
                environment,
                "CBRA_OPENAI_REASONING_EFFORT",
            ),
            text_verbosity=_required_environment_value(
                environment,
                "CBRA_OPENAI_TEXT_VERBOSITY",
            ),
            max_input_chars=_required_integer(
                environment,
                "CBRA_OPENAI_MAX_INPUT_CHARS",
            ),
            max_output_tokens=_required_integer(
                environment,
                "CBRA_OPENAI_MAX_OUTPUT_TOKENS",
            ),
            max_output_chars=_required_integer(
                environment,
                "CBRA_OPENAI_MAX_OUTPUT_CHARS",
            ),
            timeout_seconds=_required_finite_number(
                environment,
                "CBRA_OPENAI_TIMEOUT_SECONDS",
            ),
        )
    except ApplicationRendererActivationError:
        raise
    except (TypeError, ValueError):
        raise ApplicationRendererActivationError(
            "OpenAI renderer configuration is invalid"
        ) from None


def _load_openai_client_class():
    try:
        from openai import OpenAI
    except Exception:
        raise ApplicationRendererActivationError(
            "OpenAI renderer activation requires the OpenAI Python SDK"
        ) from None
    return OpenAI


def _close_quietly(client: object) -> None:
    try:
        close = getattr(client, "close", None)
        if callable(close):
            close()
    except Exception:
        pass


def application_renderer_from_environment(
    environment: Optional[Mapping[str, str]] = None,
) -> ApplicationRendererActivation:
    """Resolve one immutable process-start renderer configuration."""
    source = os.environ if environment is None else environment
    selector = _environment_value(
        source,
        RENDERER_SELECTOR_ENVIRONMENT_VARIABLE,
    )
    if selector is None or selector == NATIVE_TEMPLATE_RENDERER:
        return ApplicationRendererActivation()
    if selector != OPENAI_RESPONSES_RENDERER:
        raise ApplicationRendererActivationError(
            "{0} must be native-template or openai-responses".format(
                RENDERER_SELECTOR_ENVIRONMENT_VARIABLE
            )
        )

    for name in _AMBIENT_OPENAI_OVERRIDES:
        if _environment_value(source, name) is not None:
            raise ApplicationRendererActivationError(
                "OpenAI renderer activation does not permit {0}".format(name)
            )

    values = {
        name: _required_environment_value(source, name)
        for name in _OPENAI_REQUIRED_ENVIRONMENT_VARIABLES
    }
    configuration = _configuration_from_environment(values)
    api_key = values["OPENAI_API_KEY"]

    client_class = _load_openai_client_class()
    try:
        client = client_class(
            api_key=api_key,
            base_url=_OPENAI_API_BASE_URL,
            max_retries=0,
            timeout=configuration.timeout_seconds,
        )
    except Exception:
        raise ApplicationRendererActivationError(
            "OpenAI client could not be constructed"
        ) from None
    try:
        renderer = OpenAIResponsesArticulationRenderer(
            client,
            configuration,
        )
        return ApplicationRendererActivation(
            renderer=renderer,
            renderer_binding=renderer.binding,
            _client=client,
        )
    except Exception:
        _close_quietly(client)
        raise ApplicationRendererActivationError(
            "OpenAI renderer could not be constructed"
        ) from None
