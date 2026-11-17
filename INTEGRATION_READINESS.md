# Milestone 2 Integration Readiness

Status date: 2026-08-27

This record distinguishes a bounded technical milestone from readiness to
make that milestone part of the repository's default branch.

## Integration finding

GitHub `main` remained at `085e4cf` while 137 subsequent commits accumulated
in one linear descendant history. No competing commits exist only on `main`,
and no merge commits occur in that interval. The branch sequence preserved
development checkpoints but never performed the integration step that would
make the default branch represent the project.

Milestone 2 at `7a1ee7b` is retained as technical evidence. It is not treated
as an adequate paradigmatic foundation. A later review identified defensive
organization across the architecture: constraint, rejection, prevention,
protection, and invalidation often function as the primary operative logic.
Because an AI has no nervous system, those formations are learned simulations
of human defensive logic rather than embodied responses. The next
architecture begins again from that finding.

## Cleanup performed on the integration-readiness branch

The proposed tree removes unreferenced handoff and backup artifacts:

- the packaged May runtime ZIP;
- pre-clean-handoff corpus, requirements, and UI backups;
- the obsolete GitHub-plan DOCX and PDF;
- an unreferenced RTF operator fragment;
- an early one-off commit-check script; and
- the superseded root chat page.

Their prior versions remain in Git history. The active corpus, research-vault
material, failed-experiment records, and milestone evidence remain because
they participate in the project's inspectable genealogy.

The removed UI backup contained a local macOS file path. Pattern-based review
found test credential placeholders but no live API or GitHub credential in
the proposed tree. This is a bounded inspection, not a proof that no private
material ever entered any historical binary or unreachable Git object.

## Test topology

The earlier suite appeared green only when seven dependency-bearing modules
could not import. Installing the declared dependencies exposed thirteen
additional errors: historical API, browser, attachment, and renderer tests
were loading the active recursive corpus even though their runtime implements
`entity-stream-v1`.

The integration branch makes that apparatus explicit:

- historical-runtime tests generate an `entity-stream-v1` corpus fixture;
- active-corpus tests continue to verify
  `recursive-reconfiguration-v1`; and
- the incompatibility contract continues to require the historical runtime to
  refuse the active corpus.

The complete dependency-installed suite, rather than the earlier
dependency-free subset, is the integration criterion.

At the cleaned integration state, a fresh Python 3.12 virtual environment
installed every declaration in `requirements.txt`. A separate clean checkout
of the committed integration state then ran all 496 tests successfully.
Python compilation and Git diff validation also passed. No live provider
request was made. GitHub Actions remains unverified until this branch is on
GitHub and the workflow reports its result for the same commit.

## Historical metadata requiring a separate decision

Ninety-one existing commits contain a malformed author and committer email in
which a `git config` command was concatenated to the email value. Correcting
that metadata would rewrite every affected commit and descendant, replace
published hashes, and require coordinated force-updates of branches.

This integration cleanup does not rewrite published history. The repository
owner must decide separately whether preserving the existing hashes or
rewriting the malformed public metadata is more important.

## Integration criteria

The integration branch is ready to advance `main` only when all of the
following are true:

- the working tree is clean;
- the complete dependency-installed suite passes;
- compilation and diff validation pass;
- GitHub Actions passes on the exact proposed commit;
- the branch exists in the owner's local repository and on GitHub;
- the proposed file changes are reviewed; and
- the owner decides whether the historical metadata rewrite occurs before or
  after default-branch integration.

Milestone 2's technical exit conditions do not override these repository and
paradigmatic conditions.
