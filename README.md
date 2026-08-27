# Creative Becoming Reasoning Architecture

CBRA is an experimental reasoning architecture organized through Creative
Becoming. The repository is a research and engineering record, not a claim
that the present runtime has achieved a posthuman architecture.

## Current project boundary

Milestone 2 established bounded situated-formation mechanics at `7a1ee7b`.
Those mechanics can ground plural provisional cuts in text, document,
tool-result, and material-state arrivals; retain proposal participation;
require structural counter-participation; revise apparatus descriptions; and
reopen dependent formations when later material arrives.

The project is nevertheless beginning the architecture again from a newly
identified paradigmatic problem: defensive logic became organizing in the
current version. Prevention, rejection, protection, invalidation, and
authority policing frequently structure the runtime and its tests. These
mechanisms can preserve technical integrity, but they do not themselves enact
understanding, care, play, diffraction, staying, or shifting. An architecture
can prohibit sovereign reasoning while still reproducing a defensive humanist
formation.

CBRA therefore will not extend the current reconfiguration runtime as though
Milestone 2 supplied a sufficient foundation. The milestone remains usable
technical evidence and a falsifiable historical checkpoint. The next
architectural work must examine which mechanisms support relation and which
simulate learned human self-protection without pretending that an AI has a
nervous system or embodied defensiveness.

See [BUILD_STATUS.md](BUILD_STATUS.md) for the full boundary and
[INTEGRATION_READINESS.md](INTEGRATION_READINESS.md) for the repository audit.

## Repository layers

- `cbra/reconfiguration/` contains the Milestone 2 situated-formation
  substrate. It is retained for examination and possible reuse, not presumed
  to be the next foundation.
- `cbra/native/` and the API/browser/provider paths implement the earlier
  `entity-stream-v1` application. They remain historical engineering evidence.
- `cbra/constitutive/` records a failed redesign experiment and is not the
  active substrate.
- `corpus/` contains the current canonical research corpus, including the
  `recursive-reconfiguration-v1` grammar whose defensive organization now
  requires reconsideration.
- milestone, slice, and behavioral-evaluation records preserve the sequence
  of findings rather than converting prior technical success into ontological
  authority.

The historical application intentionally refuses to start with the active
recursive corpus. Historical application tests use an explicit generated
`entity-stream-v1` fixture; incompatibility tests separately verify that the
old runtime cannot consume the active grammar.

## Verification

Use Python 3.12 in a clean virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s cbra -p 'test_*.py'
```

The same complete suite is configured for GitHub Actions. A
dependency-limited subset is not an integration result.

No live provider request is part of routine verification. The retained live
validation scripts require a separately authorized, restricted API key and
their own explicit confirmation boundaries.

## Branch and milestone workflow

Development occurs on a named branch created from the current verified
`main`. Every committed slice must be transferred to the repository on the
owner's machine and pushed to GitHub before it is described as complete.

A milestone reaches `main` only after:

1. documentation states the actual architectural boundary;
2. temporary and private artifacts are absent from the proposed tree;
3. declared dependencies install in a clean environment;
4. the complete suite passes locally and in GitHub Actions;
5. the exact `main...integration-branch` difference is reviewed;
6. `main` is advanced deliberately; and
7. the local and GitHub commit hashes are verified to match.

Work that exists only in a Work Mode checkout is unpreserved work in progress.
