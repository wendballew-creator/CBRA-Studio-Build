from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from cbra.cbra_runtime_rebuilt.runtime.field_state import FieldState
from cbra.cbra_runtime_rebuilt.runtime.history import FieldHistoryEntry
from cbra.cbra_runtime_rebuilt.runtime.runtime_loop import run_until_articulation
from cbra.cbra_runtime_rebuilt.runtime.snapshot import build_snapshot_payload
from cbra.cbra_runtime_rebuilt.runtime.debug_payload import build_debug_payload

@dataclass
class RuntimeSession:
    state: FieldState
    history: list[FieldHistoryEntry] = field(default_factory=list)
    last_text: str = ""
    def run(self, max_steps: int = 8) -> str:
        text, _traces, _reintegrations, new_history = run_until_articulation(self.state, max_steps=max_steps)
        self.last_text = text
        self.history = list(new_history)
        return text
    def debug_payload(self) -> dict[str, Any]:
        return build_debug_payload(self.state, self.history)
    def snapshot_payload(self) -> dict[str, Any]:
        return build_snapshot_payload(self.state, self.history)
