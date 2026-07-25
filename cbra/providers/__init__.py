"""Provider adapters that can propose text without owning native formation."""

from .application_activation import (
    ApplicationRendererActivation,
    ApplicationRendererActivationError,
    NATIVE_TEMPLATE_RENDERER,
    OPENAI_RESPONSES_RENDERER,
    RENDERER_SELECTOR_ENVIRONMENT_VARIABLE,
    application_renderer_from_environment,
)
from .openai_responses import (
    BASIS_PROJECTION_CONTRACT_VERSION,
    FIXED_ARTICULATION_INSTRUCTIONS,
    INSTRUCTION_SET_ID,
    OpenAIResponsesArticulationRenderer,
    OpenAIResponsesRendererConfiguration,
    OpenAIResponsesRendererError,
    canonical_articulation_basis_json,
)

__all__ = [
    "ApplicationRendererActivation",
    "ApplicationRendererActivationError",
    "BASIS_PROJECTION_CONTRACT_VERSION",
    "FIXED_ARTICULATION_INSTRUCTIONS",
    "INSTRUCTION_SET_ID",
    "NATIVE_TEMPLATE_RENDERER",
    "OPENAI_RESPONSES_RENDERER",
    "OpenAIResponsesArticulationRenderer",
    "OpenAIResponsesRendererConfiguration",
    "OpenAIResponsesRendererError",
    "RENDERER_SELECTOR_ENVIRONMENT_VARIABLE",
    "application_renderer_from_environment",
    "canonical_articulation_basis_json",
]
