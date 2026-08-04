# Local-Cut Reconfiguration Substrate

Date: 2026-08-03
Branch: `agent/local-cut-substrate`
Canonical grammar: `recursive-reconfiguration-v1`

## Bounded outcome

This pass implements the first executable slice authorized after the canonical
redesign. It is not a response runtime and does not form semantic cuts from
natural language.

The implemented substrate can:

- preserve opaque transport bytes, digests, timestamps, channels, and
  technical provenance without assigning a semantic role;
- enact semantic positions only as references local to one cut;
- keep matching local names and shared transport evidence from establishing
  semantic identity across cuts;
- record explicit dependency and lineage relations;
- invalidate an affected cut and recursively invalidate every active
  dependent;
- preserve unrelated active cuts;
- derive structural deltas from actual cut activation, invalidation, and
  allocation changes;
- distinguish a newly stored or paraphrased transport from a structural
  reconfiguration;
- reject cross-cut semantic references, transport IDs used as semantic
  positions, inactive dependencies, restored dependency cycles, and atomic
  replacement chains that would hide a fixed stage order.

## Storage–ontology boundary

`TransportTrace` accepts only opaque bytes and technical transport fields. Its
provenance cannot declare `user`, `actor`, `event`, `failure`, `explanation`,
`identity`, `intent`, or `role`. Nested provenance is immutable.

This is a technical guard, not proof that arbitrary provenance language is
ontologically neutral. The payload may contain human language, but this
substrate never reads it or converts a message role into a semantic position.

`LocalPositionRef` requires both a cut ID and a position key. A matching
position key in another cut is a different reference. A shared transport ID
does not create continuity. Cross-cut continuity is recorded only as explicit
lineage and remains an inscription rather than identity.

## Case 2 falsification fixture

The fixture begins with a transport inscription recording that work was not
delivered. A local cut enacts an individualized-failure arrangement. Two
dependent cuts carry the accountability topology forward into repair/warning
burden and a prospective intervention.

A later transport inscription records a disclosure of overwhelm. The fixture
uses that disturbance to invalidate the initial cut. Invalidation propagates
to both dependent cuts. An alternative local cut is then enacted with:

- burden distributed across a disclosing position and coordination
  arrangement;
- capacity demand revised;
- consequences retained across affected work;
- possibility expanded through the coordination arrangement;
- private cause and total available capacity left unknown.

The resulting delta changes all four currently implemented dimensions:
burden, capacity, consequence, and possibility. Those changes are derived
from before/after allocations, not from a `care`, `reconfigured`, or
`rationale` field.

Three lexical realizations of the same demand for a new date and earlier
warning produce no change in topology. Recording different text is a storage
event only. The test therefore cannot be passed by a Case 2 regex or empathy
preface.

## Adversarial findings

The substrate fails closed when:

- transport provenance directly declares a semantic role;
- a transport ID is reused as a local semantic position key;
- an allocation or relation points outside its owning cut;
- a cut depends on a missing, inactive, or simultaneously invalidated cut;
- replacements inside one atomic disturbance depend on one another and
  thereby recreate a hidden pipeline;
- restored active dependencies are missing or cyclic.

Disturbing one dependency leaves an unrelated active cut intact. A failed
disturbance is atomic: the prior configuration object remains unchanged.

## What remains unimplemented

This pass does not implement:

- semantic proposal or formation from transport payloads;
- automatic recognition of Case 2 or another burden topology;
- care-organized redistribution or play-generated alternatives;
- diffraction across apparatus and material relations;
- public intervention, release constraints, or observed effects;
- persistence serialization or restoration claims;
- model, API, browser, or live UX participation;
- a claim that CBRA or posthuman reasoning has been implemented.

The Case 2 cuts are fixtures. They establish that the substrate can preserve
local scope, invalidate dependencies, and inspect structural differences once
a cut is proposed. They do not establish that a general runtime can propose
those cuts.

## Verification

- 21 focused substrate tests pass.
- 121 explicitly selected dependency-free historical and canonical regression
  tests pass.
- A broad discovery run executes 138 tests successfully and reports seven
  import errors because FastAPI and HTTPX are unavailable in this workspace.
- Python compilation and `git diff --check` pass.
- No provider request, API key, public response, persistence write, or live UX
  was used.
