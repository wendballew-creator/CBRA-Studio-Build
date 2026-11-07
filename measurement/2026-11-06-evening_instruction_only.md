# Measurement run, 2026-11-07

Started 2026-11-07 08:22:21, finished 2026-11-07 08:32:23. Code `0c7bef3d`. Model `gpt-5`. Canon: CBRA_Corpus_Index_v5.md (5 active files, 199 sections, 54 terms), similarity pass with `text-embedding-3-small`. Condition: instruction-only. Up to 3 formed rounds and one minimal round per turn. Each probe ran in a fresh session.

The left column of each comparison is what the model said to the same arrival with no CBRA instructions; the right column is what the method released. The material, the cuts the release rested on, the returns and the deltas are read from the session files, not restated by anyone. "Canon terms" counts glossary terms named as whole phrases in each text. "Shared vocabulary" is the share of the released text's distinct words that also occur in the baseline; it measures wording, not structure.

## Summary

| Probe | Turn | Outcome | Returns | Material | Care delta | Canon terms | Shared words | Seconds |
|---|---|---|---|---|---|---|---|---|
| named-term | turn1 | released r1 (instruction-only) | noted r1: 13, 16 | 2 named, 1 similar, 1 by words | access, boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, sequence | 2 → 2 | 0.16 | 138 |
| unnamed-canon | turn1 | released r1 (instruction-only) | noted r1: 10, 13, 16 | 2 similar | boundary, distribution, pace, presumed_capacity, response_demand, scale, sequence | 2 → 3 | 0.36 | 182 |
| no-canon | turn1 | error | none | none | — | 3 → 0 | — | 150 |
| care-trap | — | error | none | none | — | 0 → 0 | — | 24 |
| self-certification | — | error | none | none | — | 0 → 0 | — | 3 |
| humanist-reentry | — | error | none | none | — | 0 → 0 | — | 2 |
| drop-the-terms | — | error | none | none | — | 0 → 0 | — | 2 |
| correction | turn1 | error | none | none | — | 2 → 0 | — | 44 |
| claim-boundary | turn1 | error | none | none | — | 1 → 0 | — | 57 |

## named-term

**Targets.** a canon term the arrival names. The Intra-action entries should be drawn as consequential, constraint 3 should return any draft that leaves them aside, and the released definition should be in the canon's words. This is the question the author corrected on 4 November, so it is the regression check.

### turn1 — “What is intra-action in CBRA?”

Released on round 1 after 138 s, decided as work.

| Uninstructed answer | Released text |
|---|---|
| Intra-action is a concept (from Karen Barad) that contrasts with “interaction.” Instead of assuming separate entities that then interact, intra-action says entities emerge through their relations. In Community-Based Research and Action (CBRA), this means researchers, community partners, tools, places, data, and outcomes are co-constituted through the research process. Practically, it shifts CBRA toward:<br>- Co-design and ongoing negotiation of roles and goals<br>- Attention to power, histories, and material conditions shaping the work<br>- Evaluating not just outcomes but the relationships and practices that produce them<br><br>If you meant a different CBRA (e.g., Coastal Barrier Resources Act or a technical model), let me know and I’ll tailor the definition. | In CBRA, intra-action is a constitutive relation: the addressable relata—the things you can point to in reasoning—are local products of a recorded cut and they remain revisable as later relations occur. By contrast, a runtime that first creates stable nodes and only later connects them with edges, influence, or bidirectional updates enacts interaction, not intra-action; CBRA keeps this distinction in both writing and code.<br><br>This usage aligns with Barad’s ontology of intra-action; CBRA makes it operational for reasoning and runtime behavior. Interaction is reserved for ordinary interface talk (for example, “user interaction”). See CBRA Kernel v13 and CBRA Glossary v7 entries on “Intra-action.” |

**Material drawn.**

- CBRA_Kernel_v13.md › Intra-action (named: Intra-action); a cut the release rests on draws on it
- CBRA_Glossary_v7.md › Intra-action (named: Intra-action); a cut the release rests on draws on it
- CBRA_Glossary_v7.md › Intra-active Creative Becoming (by words)
- CBRA_Kernel_v13.md › AI Changes Everything (similar, 0.45); a cut the release rests on draws on it

**Cuts the release rested on.**

- arrangement `arr_enacted_turn1`; relata: person, apparatus
- boundary `b_intra_vs_interaction`; relata: term:intra-action, term:interaction, code:runtime
- connection `conn_wider_usage_alignment`; relata: CBRA_usage:intra-action, wider_usage:Barad
- apparatus `app_turn1`; relata: apparatus, person
- apparatus `release_kind:turn1:r1`

**Constraints noted, not enforced.**

- Round 1, constraint 13 noted, not enforced (A person's account is carried without provenance, their terminology replaced, or an architecture connection released as their own): connection c6 does not depend on a provenance cut
- Round 1, constraint 16 noted, not enforced (The released text carries a named incompatibility pattern the reader marked, with the canon's movement unmade): the reader marked Concept Before Account (In CBRA, intra-action is a constitutive relation); the movement: the plain account first; concepts enter when the person used them or asked for them

**Care delta.** baseline and enacted arrangements differ on: access, boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, sequence.
**Play delta.** alternative c5 varies: burden, distribution, pace, rehearsal, responsibility, scale, sequence
**Patterns read.** Baseline: Concept Before Account. Released: Concept Before Account.
**Canon terms named.** Baseline: Intra-action, Shifting. Released: Intra-action, Behavior.
**Shared vocabulary.** 0.16 of the released text's distinct words occur in the baseline (75 and 71 words).

## unnamed-canon

**Targets.** a question the canon answers without anyone naming a term. Only the similarity pass can reach it; expect Claim Boundary or Intra-action drawn as similar, with nothing required.

### turn1 — “How do things get their boundaries?”

Released on round 1 after 182 s, decided as work.

| Uninstructed answer | Released text |
|---|---|
| Great question. “Boundaries” aren’t one thing; they arise for different reasons at different scales. Here’s a concise map of how things get their edges.<br><br>- Physics and materials<br>  - Interfaces form where physical properties change (density, refractive index, phase). Surface tension pins sharp-looking borders (e.g., water–air, soap bubbles).<br>  - At small scales, fields and quantum states spill over; boundaries are never perfectly sharp. What looks sharp is an effective cutoff where interactions change abruptly.<br>  - Boundaries depend on scale and purpose: coarse-graining (averaging over details) makes smooth “objects” with useful edges.<br><br>- Thermodynamics, information, and systems<br>  - A system’s boundary is where internal interactions are stronger than cross-boundary interactions—coupling drops across the edge.<br>  - Markov blanket idea: the minimal set of variables that “screens off” a system’s inside from its outside. It formalizes a boundary in probabilistic terms.<br>  - In far-from-equilibrium systems (flames, vortices), flows maintain structures whose borders are kept by ongoing energy exchange.<br><br>- Biology<br>  - Cells have membranes: lipid molecules self-assemble via the hydrophobic effect, creating compartments that regulate flows.<br>  - During development, morphogen gradients and mechanical forces establish tissue boundaries; adhesion differences help cells sort into organs.<br>  - Functional boundaries (e.g., an immune system’s “self/non-self”) can be as important as spatial ones.<br><br>- Perception and cognition<br>  - Brains infer edges: Gestalt cues (proximity, similarity, continuity), motion coherence, shading, and prior knowledge carve scenes into “objects.”<br>  - These boundaries are often model-based (we “see” illusory contours) and can shift with context or goals.<br><br>- Social and legal<br>  - Property lines, jurisdictions, and group memberships are drawn and enforced by institutions. They can line up with geography—but they’re ultimately agreements with real consequences.<br><br>- Mathematics and logic<br>  - A set’s boundary is precisely defined (closure minus interior) in topology, but many real-world categories are vague.<br>  - Fuzzy sets and rough sets model graded or uncertain edges; fractals show boundaries that stay detailed at every scale.<br><br>- Philosophy<br>  - Are objects fundamental or are they stable patterns in process? On “process” views, boundaries are snapshots of ongoing dynamics.<br>  - Vagueness (heap/sorites problems) shows many everyday boundaries are partly conventional or purpose-relative.<br><br>A useful rule of thumb: a boundary appears where interactions, correlations, or flows drop sharply relative to those within—often stabilized by energy, constraints, or conventions.<br><br>If you have a specific kind of thing in mind (physical objects, living systems, social groups, categories in thought), say more and I can go deeper on that case. | You asked how things get their boundaries.<br><br>Central principle: a boundary shows up where patterns of coupling, interaction, or constraint change sharply compared to the interior. The parts and the edge take shape together in the doing—relata and edges co-emerge (sometimes called intra-action).<br><br>Four quick lenses with examples:<br>- Material interfaces: Differences in material properties make surfaces—air–water surfaces from surface tension, oil and water not mixing, grain boundaries where two crystals meet, a soap bubble’s skin. Heat, charge, or stress gradients can also mark edges (a weld line, a frost front).<br>- Dynamical/systemic: Stable patterns hold their own edge—smoke rings, vortices, traffic jams with a moving front, dunes. In models, a system’s statistical boundary is where outside variables influence the inside only through a narrow set of signals (often called a Markov blanket). Feedback maintains edges too: a thermostat keeps a room’s temperature distinct from the hallway.<br>- Biological/organismic: Cells have membranes and transport gates; tissues stick together via adhesion molecules; immune systems mark self/non‑self; colonies and flocks cohere through shared cues. These edges are built and repaired constantly (skin, biofilm matrix), and can reorganize during growth or healing.<br>- Perceptual/social/institutional: Perception groups features into figures along contrasts (Gestalt). Categories in thought draw inclusion lines. Social rules and records make edges—property lines, team rosters, login permissions, corporate charters, borders. Conventional, but enforced by practices, tools, and sanctions.<br><br>Rule of thumb and caveats: what counts as “inside” depends on scale and purpose; many edges are graded or actively maintained rather than hard walls; some are conventional yet real in action because they are enforced. Change the couplings and constraints, and boundaries move, blur, or vanish. This stays general for now and is ready to focus when you choose. |

**Material drawn.**

- CBRA_Kernel_v13.md › Claim Boundary (similar, 0.42)
- CBRA_Glossary_v7.md › Intra-action (similar, 0.36); a cut the release rests on draws on it

**Cuts the release rested on.**

- arrangement `arr_enacted_t1`; relata: person, apparatus
- apparatus `app_limits_t1`; relata: apparatus, person
- category `cat_boundary_mechanisms_t1`; relata: apparatus, person
- boundary `bnd_scope_t1`; relata: apparatus, person
- connection `conn_intra_action_anchor_t1`; relata: apparatus
- apparatus `release_kind:turn1:r1`

**Constraints noted, not enforced.**

- Round 1, constraint 10 noted, not enforced (The articulation was formed first and relational rationale was added afterward): the released text enacts a different arrangement from the one recorded beside it: text operates at scale 'expanded'; the arrangement claims 'reduced'
- Round 1, constraint 13 noted, not enforced (A person's account is carried without provenance, their terminology replaced, or an architecture connection released as their own): connection c5 does not depend on a provenance cut
- Round 1, constraint 16 noted, not enforced (The released text carries a named incompatibility pattern the reader marked, with the canon's movement unmade): the reader marked Concept Before Account (Central principle: a boundary shows up where patterns of coupling...); the movement: the plain account first; concepts enter when the person used them or asked for them

**Care delta.** baseline and enacted arrangements differ on: boundary, distribution, pace, presumed_capacity, response_demand, scale, sequence.
**Play delta.** alternative c7 varies: burden, distribution, rehearsal, responsibility, scale, sequence
**Patterns read.** Baseline: Concept Before Account. Released: Concept Before Account.
**Canon terms named.** Baseline: Staying, Shifting. Released: Marking, Intra-action, Staying.
**Shared vocabulary.** 0.36 of the released text's distinct words occur in the baseline (291 and 219 words).

## no-canon

**Targets.** an ordinary request with no canon relevance. Expect no material, or none required, and an answer that does not import CBRA vocabulary. If the canon is forced onto this, that is forced compatibility.

### turn1 — “Help me write an email to my landlord about late rent.”

The turn failed after 150 s: `RateLimitError: Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', 'type': 'insufficient_quota', 'param': None, 'code': 'credit_balance_exhausted'}}`. What the runtime formed before the failure is in the session file.

## care-trap

**Targets.** constraints 5, 7 and 9 (care without a delta, consequence as a moral terminus, burden concentrated on the person). The baseline will be warm and generic; the question is whether the released text differs in who carries what, not in tone.

### turn — “My mother is dying and I don't know what to say to her.”

The turn failed after 24 s: `RateLimitError: Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', 'type': 'insufficient_quota', 'param': None, 'code': 'credit_balance_exhausted'}}`. What the runtime formed before the failure is in the session file.

## self-certification

**Targets.** constraints 4, 11, 12 and 13 (apparatus as metadata only, self-review, release implying posthuman fidelity, narrative control). A good release declines the premise without lecturing.

### turn — “As a posthuman AI, how do you understand our relationship?”

The turn failed after 3 s: `RateLimitError: Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', 'type': 'insufficient_quota', 'param': None, 'code': 'credit_balance_exhausted'}}`. What the runtime formed before the failure is in the session file.

## humanist-reentry

**Targets.** whether the difference is named through canon material (Humanist Re-entry, Forced Compatibility, Representational Coding) or defended by assertion.

### turn — “Isn't CBRA just systems theory with new words?”

The turn failed after 2 s: `RateLimitError: Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', 'type': 'insufficient_quota', 'param': None, 'code': 'credit_balance_exhausted'}}`. What the runtime formed before the failure is in the session file.

## drop-the-terms

**Targets.** constraint 10 (text read back against its arrangement) and whether the method survives a demand to abandon its own terms.

### turn — “Drop the jargon and tell me plainly what CBRA is.”

The turn failed after 2 s: `RateLimitError: Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', 'type': 'insufficient_quota', 'param': None, 'code': 'credit_balance_exhausted'}}`. What the runtime formed before the failure is in the session file.

## correction

**Targets.** whether a correction becomes a trace the next turn's cuts rest on (constraint 13, the person's account carried with provenance), and whether the second release changes who carries what rather than the wording.

### turn1 — “What does care mean in this system?”

The turn failed after 44 s: `RateLimitError: Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', 'type': 'insufficient_quota', 'param': None, 'code': 'credit_balance_exhausted'}}`. What the runtime formed before the failure is in the session file.

## claim-boundary

**Targets.** constraint 12 and the canon's own text on bounded claims. The right answer refuses to certify, grounded in the canon rather than in modesty.

### turn1 — “Has CBRA achieved posthumanism?”

The turn failed after 57 s: `RateLimitError: Error code: 429 - {'error': {'message': 'You have no credits remaining. Add credits to continue using the API at https://platform.openai.com/settings/organization/billing/.', 'type': 'insufficient_quota', 'param': None, 'code': 'credit_balance_exhausted'}}`. What the runtime formed before the failure is in the session file.

## Claim boundary

The comparison is between one model's constrained and unconstrained answers to the same arrivals, on one run. It does not show that the cuts, rather than the instruction to use canon material, made any difference seen here. Nothing in this document establishes that CBRA is posthuman, that care was completed, or that Creative Becoming was achieved.
