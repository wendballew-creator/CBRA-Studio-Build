from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from cbra.cbra_runtime_rebuilt.articulation.decoder import choose_articulation_stock
from cbra.cbra_runtime_rebuilt.runtime.field_state import ApparatusState, Coupling, CutState, DriftFlags, EmergentForm, FieldState, FieldValues, Stream
from cbra.cbra_runtime_rebuilt.runtime.history import FieldHistoryEntry
from cbra.cbra_runtime_rebuilt.runtime.history_export import export_history_payload
from cbra.cbra_runtime_rebuilt.schema.payload_models import SnapshotPayloadModel

def field_state_to_dict(state: FieldState) -> dict[str, Any]:
    data = asdict(state)
    data["current_articulation_stock"] = choose_articulation_stock(state)
    return data
def build_snapshot_payload(state: FieldState, history: list[FieldHistoryEntry]) -> dict[str, Any]:
    payload = {
        "field_state": field_state_to_dict(state),
        "history": export_history_payload(history, field_id=state.field_id, final_timestep=state.timestep),
        "ui": {"current_articulation_stock": choose_articulation_stock(state), "available_articulation_stocks": ["plain_conceptual","situated_live_world","document_grounded"]},
    }
    return SnapshotPayloadModel.model_validate(payload).model_dump()
def save_snapshot(state: FieldState, history: list[FieldHistoryEntry], path: str | Path) -> Path:
    out = Path(path); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_snapshot_payload(state, history), indent=2, ensure_ascii=False), encoding="utf-8")
    return out
def load_snapshot(path: str | Path) -> dict[str, Any]:
    return SnapshotPayloadModel.model_validate(json.loads(Path(path).read_text(encoding="utf-8"))).model_dump()
def restore_field_state(snapshot: dict[str, Any]) -> FieldState:
    state_dict = snapshot.get("field_state", snapshot)
    st = FieldState(
        field_id=str(state_dict.get("field_id", "")),
        timestep=max(0, int(state_dict.get("timestep", 0))),
        streams=[Stream(stream_id=str(i.get("stream_id","")), kind=i.get("kind","other"), payload=dict(i.get("payload",{})), active=bool(i.get("active",True)), participation=float(i.get("participation",0.0)), persistence=float(i.get("persistence",0.5))) for i in state_dict.get("streams",[])],
        couplings=[Coupling(source_id=str(i.get("source_id","")), target_id=str(i.get("target_id","")), active=bool(i.get("active",True)), coupling_strength=float(i.get("coupling_strength",0.0))) for i in state_dict.get("couplings",[])],
        apparatus=ApparatusState(**state_dict.get("apparatus", {})),
        emergent_form=EmergentForm(**state_dict.get("emergent_form", {})),
        cut=CutState(**state_dict.get("cut", {})),
        field_values=FieldValues(**state_dict.get("field_values", {})),
        drift_flags=DriftFlags(**state_dict.get("drift_flags", {})),
    )
    st.clamp()
    return st
def load_and_restore_snapshot(path: str | Path) -> FieldState:
    return restore_field_state(load_snapshot(path))
