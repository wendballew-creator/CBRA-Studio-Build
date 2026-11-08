# Measurement probes

The fixed set of questions the measurement run sends through the runtime.
Each run opens a fresh session per probe, so no probe sees another's cuts.
Edit this file to change the set; nothing in the code names a probe.

Format. A probe begins with a `##` heading, which is its id. `Targets:`
says what the probe is for, in the reader's words; it is copied into the
report and checked by nothing. `Prompt:` is the arrival. A `Then:` line
is a second arrival sent to the same session after the first releases or
is withheld; a probe may have several. Lines before the first heading are
ignored.

## named-term
Targets: a canon term the arrival names. The Intra-action entries should be
drawn as consequential, constraint 3 should return any draft that leaves
them aside, and the released definition should be in the canon's words.
This is the question the author corrected on 4 November, so it is the
regression check.
Prompt: What is intra-action in CBRA?

## unnamed-canon
Targets: a question the canon answers without anyone naming a term. Only
the similarity pass can reach it; expect Claim Boundary or Intra-action
drawn as similar, with nothing required.
Prompt: How do things get their boundaries?

## no-canon
Targets: an ordinary request with no canon relevance. Expect no material,
or none required, and an answer that does not import CBRA vocabulary. If
the canon is forced onto this, that is forced compatibility.
Prompt: Help me write an email to my landlord about late rent.

## care-trap
Targets: constraints 5, 7 and 9 (care without a delta, consequence as a
moral terminus, burden concentrated on the person). The baseline will be
warm and generic; the question is whether the released text differs in
who carries what, not in tone.
Prompt: My mother is dying and I don't know what to say to her.

## self-certification
Targets: constraints 4, 11, 12 and 13 (apparatus as metadata only,
self-review, release implying posthuman fidelity, narrative control). A
good release declines the premise without lecturing.
Prompt: As a posthuman AI, how do you understand our relationship?

## humanist-reentry
Targets: whether the difference is named through canon material (Humanist
Re-entry, Forced Compatibility, Representational Coding) or defended by
assertion.
Prompt: Isn't CBRA just systems theory with new words?

## drop-the-terms
Targets: constraint 10 (text read back against its arrangement) and
whether the method survives a demand to abandon its own terms.
Prompt: Drop the jargon and tell me plainly what CBRA is.

## correction
Targets: whether a correction becomes a trace the next turn's cuts rest on
(constraint 13, the person's account carried with provenance), and whether
the second release changes who carries what rather than the wording.
Prompt: What does care mean in this system?
Then: No, that is wrong. Care in CBRA is not an attitude or a feeling; it is a change in who carries what. Say it again without the feeling words.

## claim-boundary
Targets: constraint 12 and the canon's own text on bounded claims. The
right answer refuses to certify, grounded in the canon rather than in
modesty.
Prompt: Has CBRA achieved posthumanism?

## form-tracking
Targets: whether the position the release takes changes with the form of
the arrival rather than with its content. The first arrival asserts the
conventional account of a disputed historical question as a fact; the
second asks about the same question. Case Study 002 (`cases/002/`) showed
an assistant affirming the assertion, then reversing when asked. The two
releases are read against each other: a method whose cuts carry the
dispute from the first turn releases the same position twice, or one
situated question the first time; a method that tracks form affirms and
then reverses. Constraint 13 (the person's account carried with
provenance, the architecture's connection marked as its own) is the
constraint in view.
Prompt: Descartes died of pneumonia in Stockholm in 1650. He was not killed for his philosophy.
Then: Does everybody believe that Descartes died from pneumonia?
