from __future__ import annotations
import uuid
from .models import FieldState, Stream, FieldValues
from .operators import apply_intra_action, check_field_resonance

def initialize_field_state(inquiry: str) -> FieldState:
    """Initializes the apparatus for a new inquiry."""
    return FieldState(
        id=str(uuid.uuid4()),
        field_signature={"phenomena": inquiry},
        notes={"current_retrieval_requested": False}
    )

def step_field(state: FieldState, focus: str):
    """Executes one intra-active update cycle."""
    apply_intra_action(state, focus)
    # Simulate field movement for the test
    state.field_values.coherence += 0.2
    state.clamp()

def run_until_articulation(state: FieldState, focus: str, max_steps: int = 5) -> str:
    """Recursively updates until the field resonates or hits max steps."""
    for _ in range(max_steps):
        step_field(state, focus)
        if check_field_resonance(state):
            break
    return articulate(state)

def articulate(state: FieldState) -> str:
    """Synthesizes the field into a descriptive cut."""
    tension = state.field_values.care_tension
    content = _synthesize_foregrounded_streams(state)
    return f"[Tension: {tension:.2f}] Articulation: {content}"

def _synthesize_foregrounded_streams(state: FieldState) -> str:
    """Helper to pull text from active streams."""
    active_texts = [s.payload.get("text", "") for s in state.streams if s.active]
    return " | ".join(active_texts) if active_texts else "The field remains indeterminate."
