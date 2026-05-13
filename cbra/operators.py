from .models import FieldState, Stream, FieldValues

def reintegrate_field(state: FieldState):
    """Resets the field values when the system becomes too rigid."""
    state.field_values.cut_permeability = 1.0
    state.field_values.cut_pressure = 0.2
    state.field_values.openness = 0.8
    state.clear_drift_flags()

def apply_intra_action(state: FieldState, focus: str):
    """Adjusts field values based on the resonance between streams and the current focus."""
    state.field_values.care_tension += 0.05
    state.timestep += 1
    
    # Trigger LiveWorld if the field is under high tension but low coherence
    if state.field_values.care_tension > 0.6 and state.field_values.coherence < 0.4:
        live_world_operator(state, focus)

    if state.drift_flags.interpretive_compression:
        reintegrate_field(state)

def live_world_operator(state: FieldState, focus: str):
    """
    Operator: LiveWorld.
    Simulates the intake of live-world material (APIs/Search) into the field.
    """
    # In a production environment, this would call your search/Gmail API
    new_material = f"Live-world trace for '{focus}' detected at timestep {state.timestep}"
    
    incoming_stream = Stream(
        stream_id=f"live_{state.timestep}",
        kind="live_world",
        payload={"text": new_material},
        participation=0.8
    )
    
    state.streams.append(incoming_stream)
    # The influx of new material increases openness and permeability
    state.field_values.openness = 0.9
    state.field_values.cut_permeability = 0.9
    state.notes["last_live_event"] = state.timestep

def check_field_resonance(state: FieldState) -> bool:
    """Checks if the field is coherent enough to articulate."""
    return state.field_values.coherence > 0.7
