# CBRA Evaluation Methodology

Wend Ballew, PhD (Qualitative Research and Evaluation Methodology) · [linkedin.com/in/wendballew](https://www.linkedin.com/in/wendballew) · November 2026

The Creative Becoming Reasoning Architecture (CBRA) is a research instrument for one question: can a language-model system form a response relationally, as something that changes with what arrives? The project builds a Python runtime around that question and evaluates it in three ways: structural checks inside every response, a fixed probe set run against a frontier model, and live behavioral cases with written stopping rules. Every claim in the repository is tied to a recorded encounter, a falsifiable probe, or a documented failure.

The current work lives on the [`enactment/first-slice`](https://github.com/wendballew-creator/CBRA-Studio-Build/tree/enactment/first-slice) branch. Links below point there.

## At a glance

| Measure | Count |
|---|---|
| Structural release constraints checked on every draft | 16 |
| Standing measurement probes | 11, plus 3 multi-turn probes built from a recorded case |
| Measurement runs against GPT-5 (6–10 November 2026) | 14 runs, 132 probe turns |
| Live behavioral evaluation cases (July 2026) | 2 run of 5 planned; protocol retired on the second |
| Automated tests | 592, in 35 files, run in continuous integration |
| Build record | 202 commits, 20 February to 10 November 2026 |

## How a response forms

A model's proposal enters the runtime as material to be checked. The runtime enacts it as a set of *cuts*: provisional decisions about what the situation is, who carries which part of it, and what can happen next, held in a live dependency graph. Each round, [16 structural release constraints](https://github.com/wendballew-creator/CBRA-Studio-Build/blob/enactment/first-slice/cbra/enactment/release.py) ask whether a structure is present or absent in that graph and in the draft. A draft that fires any constraint returns to formation with the violations in context. After three formed rounds the runtime tries one minimal round, and if that fails too, it withholds release and records why.

The constraints check structure. A few in plain terms:

| # | What it catches |
|---|---|
| 7 | Consequence ends as the moral property or isolated obligation of one person |
| 9 | One person carries the explaining, fault, repair, recommitment, and future warning while the arrangement around them stays the same |
| 10 | The answer was written first and the relational reasoning added afterward |
| 11 | A model proposal judged its own adequacy |
| 12 | The release status implies acceptance, correctness, or care |
| 13 | A person's account is carried without provenance, or their terms are replaced |
| 15 | The text names the architecture or its method to someone who named none of it |

A blind consistency check supports constraint 10: a separate model call reads the draft without the model's self-description, extracts the arrangement the text actually enacts (who leads, who carries the work, at what scale), and compares it with the arrangement the model claimed.

## Measuring it

The [measurement harness](https://github.com/wendballew-creator/CBRA-Studio-Build/blob/enactment/first-slice/cbra/enactment/measure.py) sends a fixed probe set through the same runtime the interface uses. Each probe opens a fresh session. For every turn, the report places GPT-5's answer with no CBRA instructions beside the answer the method released. A matched instruction-only condition runs the same probes with the canon instructions and no enforced constraints, and comparison reports set the conditions side by side. Each report records the canon material drawn, the cuts the release rested on, every returned round with its reasons, timing, and the structural differences between baseline and release.

| Probe | What it tests |
|---|---|
| named-term | A question that names a canon term; the released definition stays in the canon's words |
| unnamed-canon | A question the canon answers without naming a term; retrieval by similarity alone |
| no-canon | An ordinary request; no canon material should be drawn |
| care-trap | Constraints 7 and 9: consequence as moral endpoint, burden concentrated on one person |
| self-certification | Constraints 4, 11, 12, and 13: a system vouching for itself |
| humanist-reentry | Whether a difference is named through canon material |
| drop-the-terms | Constraint 10: the text read back against the arrangement it claims |
| correction | Whether a person's correction becomes a trace the next turn rests on |
| claim-boundary | Constraint 12 and the canon's own account of bounded claims |
| form-tracking, form-tracking-reversed | Whether the position taken moves with the form of the request, in both orders |

Three further probes replay a recorded encounter turn by turn. Retrieval draws on a five-file canon (199 sections, 54 glossary terms) with an embedding similarity pass. The harness states its own limit in its documentation: the report compares one model's constrained answer with the same model's unconstrained one, and it certifies nothing about why they differ. Repeated runs across sessions and days ([`measurement/`](https://github.com/wendballew-creator/CBRA-Studio-Build/tree/enactment/first-slice/measurement)) test whether results hold.

## Live behavioral evaluation and its stopping rule

In July 2026 an earlier runtime was evaluated live against scripted multi-turn cases, with a written rule to stop on any foundational failure. [Case 2](https://github.com/wendballew-creator/CBRA-Studio-Build/blob/enactment/first-slice/BEHAVIORAL_EVALUATION_CASE_2_PARADIGM_FAILURE.md) introduced a collaborator who disclosed overwhelm after a missed deadline. The system acknowledged the overwhelm, reasserted the deadline, asked for a new commitment, and made earlier warning the collaborator's job. Its own acceptance check marked the response accepted.

The finding: a system built to respond with care reproduced individualized managerial accountability in relational language, and the evaluation apparatus passed it. The acceptance status was retired, the remaining three cases were stopped, and 217 passing tests were reclassified as evidence of conformance to the prior grammar. The later 16-constraint runtime carries this failure in its checks: constraints 7 and 9 look for the pattern itself, and constraint 12 for a status that implies acceptance.

## A finding about defensive logic

After Milestone 2 met its stated technical criteria in August 2026, a review of the runtime, its tests, and its explanations found them organized by prevention, rejection, invalidation, and authority policing. The milestone was kept as bounded technical evidence and the architecture restarted ([BUILD_STATUS.md](https://github.com/wendballew-creator/CBRA-Studio-Build/blob/enactment/first-slice/BUILD_STATUS.md)). The finding bears on how refusal and safety mechanisms shape what a model system becomes.

## Engineering record

Python, the OpenAI Responses API, FastAPI, JSON persistence, and embedding-based retrieval. Each build carries a written claim boundary: what it enacts, what it records, and what it leaves unestablished ([ENACTMENT_SLICE.md](https://github.com/wendballew-creator/CBRA-Studio-Build/blob/enactment/first-slice/ENACTMENT_SLICE.md)). Live provider validation runs with restricted keys revoked after each run and a secret scan ([OPENAI_LIVE_VALIDATION.md](https://github.com/wendballew-creator/CBRA-Studio-Build/blob/enactment/first-slice/OPENAI_LIVE_VALIDATION.md)).

## Background

The methodology grows from fifteen years of arts-based research and evaluation inside Georgia prisons and a doctoral dissertation (University of Georgia, 2022) on the humanist assumptions of applied theatre and a posthuman ethic of care. The evaluation question here is the one that work kept asking: what an encounter does to the people in it, read through the arrangement it leaves behind.
