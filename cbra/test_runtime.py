import pytest
from cbra.engine import initialize_field_state, step_field
from cbra.models import FieldState

def test_live_world_activation():
    """Verifies that high tension triggers the LiveWorldOperator."""
    state = initialize_field_state("Complex Inquiry")
    # Manually spike tension and keep coherence low
    state.field_values.care_tension = 0.7
    state.field_values.coherence = 0.1
    
    # This step should trigger the LiveWorldOperator
    step_field(state, "Complex Inquiry")
    
    # Check if a live_world stream was added
    live_streams = [s for s in state.streams if s.kind == "live_world"]
    assert len(live_streams) > 0
    assert state.field_values.openness == 0.9