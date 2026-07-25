"""Provider adapters that can propose text without owning native formation."""

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
    "BASIS_PROJECTION_CONTRACT_VERSION",
    "FIXED_ARTICULATION_INSTRUCTIONS",
    "INSTRUCTION_SET_ID",
    "OpenAIResponsesArticulationRenderer",
    "OpenAIResponsesRendererConfiguration",
    "OpenAIResponsesRendererError",
    "canonical_articulation_basis_json",
]
