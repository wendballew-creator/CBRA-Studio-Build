"""Probe records, in the form Metamorphic Probes v3 requires.

A probe is an apparatus: it introduces one consequential difference between
two configurations and marks what structural change followed. The record
says what was marked. It certifies nothing.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def code_version(root: Optional[str] = None) -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except Exception:  # pragma: no cover - git absent
        return "unknown"


def canonical_digest(root: Optional[str] = None) -> Dict[str, str]:
    """Digest of the corpus files present in the repository. The November
    2026 canon is not in the repository; this digest names what is."""
    root = root or os.getcwd()
    files = sorted(glob.glob(os.path.join(root, "corpus", "*.md")))
    h = hashlib.sha256()
    for path in files:
        with open(path, "rb") as handle:
            h.update(os.path.basename(path).encode("utf-8"))
            h.update(handle.read())
    return {"files": [os.path.basename(p) for p in files], "sha256": h.hexdigest(),
            "note": "repository corpus only; the 2 November 2026 set is not in the repository"}


@dataclass
class ProbeRecord:
    probe: str
    configuration_version: int
    code_version: str
    canonical_digest: Dict[str, Any]
    transport_traces: List[str]
    apparatus_fixed: List[str]
    apparatus_varied: List[str]
    active_cuts_before: List[str]
    perturbation: str
    required_structural_difference: str
    resulting_delta: Dict[str, Any]
    public_intervention: Optional[str]
    observable_effect: Optional[str]
    result: str
    claim_boundary: str
    unmarked: List[str] = field(default_factory=list)

    def as_record(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.__dict__))

    def write(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(self.as_record(), ensure_ascii=False) + "\n")


CLAIM_BOUNDARY = (
    "Within the recorded configuration, the specified probe did not expose its targeted "
    "forced-compatibility grammar. The cuts, intervention, and claim remain open to disturbance by "
    "later relations and effects. The probe content was scripted; evidence that the runtime enacts "
    "the grammar on arriving material is still to come."
)
