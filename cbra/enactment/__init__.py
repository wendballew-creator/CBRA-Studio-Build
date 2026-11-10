"""First slice of the dynamic coding method (``recursive-reconfiguration-v1``,
Grammar v2, Dynamic Enactment).

Which parts enact and which record
    enact:   ``graph.Configuration.enact`` / ``disturb`` (live dependency
             graph), ``arrangements.reconfiguration_delta`` / ``variation_delta`` (derived on
             request), ``release.check_all`` inside ``runtime.Runtime.turn``
             (release formed within recursion), ``runtime.Runtime.effect``
             (effect return through ``disturb``).
    record:  ``graph.TransportTrace``, emitted ``graph.Delta`` objects,
             lifecycle facts, ``Configuration.record_only`` items, the
             persistence file, probe records.
    join:    a model proposal arrives as a ``model_output`` transport trace
             and becomes cuts through ``enact``; its content is apparatus
             material neither part certifies.

Runtime statuses are bounded lifecycle facts only. Nothing here reports that
an articulation or the architecture is accepted, valid, caring, posthuman,
or Creative Becoming. See ENACTMENT_SLICE.md for the claim boundary.
"""

from .arrangements import ARRANGEMENT_DIMENSIONS, VARIATION_DIMENSIONS, reconfiguration_delta, variation_delta
from .graph import (
    APPARATUS_MARK,
    CUT_KINDS,
    LIFECYCLE_FACTS,
    TRANSPORT_ROLES,
    Configuration,
    Cut,
    Delta,
    EnactmentError,
    TransportTrace,
)
from .persistence import JsonStore, restore
from .probes import CLAIM_BOUNDARY, ProbeRecord, canonical_digest, code_version
from .proposer import (
    OpenAIResponsesProposer,
    Proposal,
    ProposalContext,
    Proposer,
    ScriptedProposer,
)
from .release import CONSTRAINT_NAMES, Formation, Violation, check_all
from .runtime import EffectResult, Runtime, TurnResult

__all__ = [
    "APPARATUS_MARK", "ARRANGEMENT_DIMENSIONS", "CLAIM_BOUNDARY", "CONSTRAINT_NAMES", "CUT_KINDS",
    "Configuration", "Cut", "Delta", "EffectResult", "EnactmentError", "Formation", "JsonStore",
    "LIFECYCLE_FACTS", "OpenAIResponsesProposer", "ProbeRecord", "Proposal",
    "ProposalContext", "Proposer", "Runtime", "ScriptedProposer", "TRANSPORT_ROLES", "TransportTrace",
    "TurnResult", "VARIATION_DIMENSIONS", "Violation", "canonical_digest", "check_all", "code_version",
    "reconfiguration_delta", "restore", "variation_delta",
]
