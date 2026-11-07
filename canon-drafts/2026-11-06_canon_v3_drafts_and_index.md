# Grammar v3, Glossary v7, Constraints v3 drafts and how they become active, 6 November 2026

Drafts of CBRA Recursive Reconfiguration Grammar v3, CBRA Relational
Glossary v7 and CBRA Incompatibility Constraints v3 were written on
6 November 2026 into the author's canon folder, beside the versions they
would supersede:

    .cbra-runtime/canon/CBRA_Reconfiguration_Grammar_v3.md
    .cbra-runtime/canon/CBRA_Glossary_v7.md
    .cbra-runtime/canon/CBRA_Incompatibility_Constraints_v3.md

Glossary v7 carries the nine terms and Constraints v3 the seven patterns
drafted in `2026-11-06_release_form_entries.md`, each with a Changes
section naming its source; v6 and v2 are unchanged. Where that draft left
a question for the author, the files take one answer and the author can
take another: Premature Coherence is in both the Glossary and the
Constraints; "Offer of Options" is the name used; Diagnostic Substitution
(the pattern) and Behavior and Status (the term) are kept apart.

The folder is outside the repository by the author's decision that the
November canon stays uncommitted until reviewed, so the draft is in the
author's files and not here. ## What Grammar v3 changes

- A status line marking it a draft for the author's review.
- Dynamic Enactment gains one condition: the kind of release decided from
  the cuts before any text, and the text written afterward from the cuts.
- Structural Release Constraints gains a subsection, Kind of Release, that
  says what the two kinds are, how a staying cut makes the release a
  question, that the decision is a cut the intervention depends on, that
  an offer of options is a third form and neither kind, and that the text
  is written from the cuts in a separate movement.
- The list gains constraints 14 and 15 in the wording the author chose on
  6 November 2026.
- A Changes from v2 section records all of this. Changes from v1 is kept.
- Nothing else changed.

## How they become active

The runtime reads the active files from the corpus index, and it takes the
latest index file in the folder by name. The three drafts sit in the folder
unread until an index lists them. To activate it, the author saves the text
below as `CBRA_Corpus_Index_v5.md` in the same folder (and makes any
changes to it first); from the server's next start the runtime reads v3 as
the Grammar, the material passes draw on its sections, and v2 becomes
historical. Saving the index is the author's act; nothing in this
repository does it.

## Proposed Corpus Index v5

```
# CBRA Corpus Index v5
Status: Active local constraints for the CBRA runtime corpus, pending the
author's review
Execution grammar: recursive-reconfiguration-v1
Date: 6 November 2026
Supersedes: Corpus Index v4 (2 November 2026, revised 3 November 2026)

## Canonical Files (Active, pending review)
1. CBRA_Kernel_v13.md (revised 3 November 2026)
2. CBRA_Reconfiguration_Grammar_v3.md (6 November 2026)
3. CBRA_Glossary_v7.md (6 November 2026)
4. CBRA_Incompatibility_Constraints_v3.md (6 November 2026)
5. CBRA_Metamorphic_Probes_v3.md

Companion guide: CBRA Conceptual Grounding and Systems Instructions v7
(3 November 2026; offered as canon in the glossary's sense; connects the
dissertation to the files above).

## Historical (retained as evidence and material)
- CBRA_Reconfiguration_Grammar_v2.md, CBRA_Glossary_v6.md,
  CBRA_Incompatibility_Constraints_v2.md (2 November 2026; the files Index
  v4 lists as active).
- CBRA_Kernel_v12.md, CBRA_Reconfiguration_Grammar_v1.md,
  CBRA_Glossary_v5.md, CBRA_Incompatibility_Constraints_v1.md,
  CBRA_Falsification_Probes_v2.md (28 July 2026; the set Index v3 lists
  as active, and the set the repository still carries).
- Kernel v11, Glossary v4, Drift Constraints v2, Phenomenon Formation Core
  v1, Paradigmatic Invariants v1, and the `cbra/constitutive/` slice
  (`constitutive-phenomenon-v1`).
- Kernel v10.2, Loops Core v1, Glossary v3, Drift Constraints v1
  (`entity-stream-v1`; still loaded by the main-branch prototype).

## Changes from v4
- Grammar v3 replaces Grammar v2 as the active execution contract. v3
  adds the kind of release decided from the cuts and constraints 14 and
  15, which the author chose on 6 November 2026 after the first
  measurements of the enactment slice. The runtime had enacted the two
  constraints ahead of the canon; this index closes that gap.
- Glossary v7 replaces v6 with nine new terms and Constraints v3 replaces
  v2 with seven new formation-level patterns, both drafted the same day
  from canon-drafts/2026-11-06_release_form_entries.md. Kernel v13 and
  Probes v3 are unchanged.

## Status of This Set
- Unchanged from Index v4, with one addition: Grammar v3, Glossary v7 and
  Constraints v3 were drafted on 6 November 2026 by one apparatus from
  their predecessors and the author's decisions of that day. By the Self-Certification constraint the apparatus that drafted
  it cannot certify it; the author's review is the check.

## Notes
- As in Index v4.
```

## The runtime's side

Nothing in the runtime depends on which index is active for constraints 14
and 15 to run; they run now. What the index changes is which Grammar the
material passes draw passages from, and whether the record the author
holds matches what the runtime enacts.
