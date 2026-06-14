import os
from .models import FieldState, Stream

def live_world_operator(state: FieldState, focus: str):
    """
    Operator: LiveWorld.
    Inhales material from the research_vault to inform the field.
    """
    vault_path = os.path.expanduser("~/cbra_api/research_vault")
    
    # Try to find a file that matches the 'focus' or just take the first one
    try:
        files = os.listdir(vault_path)
        if files:
            with open(os.path.join(vault_path, files[0]), 'r') as f:
                content = f.read()
            
            new_stream = Stream(
                stream_id=f"vault_{state.timestep}",
                kind="live_world",
                payload={"text": content, "source": files[0]},
                participation=0.9
            )
            state.streams.append(new_stream)
            state.notes["last_discovery"] = files[0]
            # When world enters, the 'cut' becomes more permeable (open)
            state.field_values.cut_permeability = 1.0
    except Exception as e:
        state.notes["live_world_error"] = str(e)

def apply_intra_action(state: FieldState, focus: str):
    """Standard update logic."""
    state.field_values.care_tension += 0.05
    state.timestep += 1
    
    # If tension is high, call in the LiveWorld
    if state.field_values.care_tension > 0.6:
        live_world_operator(state, focus)
