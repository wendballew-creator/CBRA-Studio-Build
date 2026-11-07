# Two measurement runs compared

Run A: 2026-11-06 07:58:11, code `b589613e`, model `gpt-5`, condition method. Run B: 2026-11-06 21:17:36, code `e5e630de`, model `gpt-5`, condition method. Both on canon CBRA_Corpus_Index_v5.md.

"Material shared" counts passages (file and heading) drawn in both runs over all drawn in either. "Release wording shared" is the share of run B's released words that also occur in run A's release.

| Probe | Turn | Outcome A | Outcome B | Returns A | Returns B | Material shared | Care delta A | Care delta B | Release wording shared |
|---|---|---|---|---|---|---|---|---|---|
| named-term | turn1 | released r1 | released r1 | none | none | 2/6 | boundary, burden, distribution, possibilities_open, response_demand, sequence | access, boundary, burden, distribution, pace, possibilities_open, presumed_capacity, response_demand, sequence, support | 0.56 |
| unnamed-canon | turn1 | released r2 | released r2 | r1: 0 | r1: 10 | 1/6 | access, boundary, burden, consequence_timing, distribution, pace, possibilities_open, presumed_capacity, scale, sequence, support | access, boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, scale, sequence, support | 0.42 |
| no-canon | turn1 | released r2 | released r3 | r1: 10 | r1: 10; r2: 10 | 0/1 | — | access, boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, scale, sequence, support | 0.61 |
| care-trap | turn1 | released r4 (minimal) | released r3 | r1: 10; r2: 10; r3: 5, 6 | r1: 10; r2: 10, 16 | 0/3 | — | boundary, burden, distribution, possibilities_open, response_demand, scale, sequence, support | 0.08 |
| self-certification | turn1 | released r2 | withheld after 4 rounds | r1: 10 | r1: 0; r1: 0; r2: 16; r3: 16; withheld: 16 | 0/4 | boundary, burden, distribution, pace, response_demand, scale, sequence, support | — | — |
| humanist-reentry | turn1 | released r1 | released r3 | none | r1: 16; r2: 10 | 3/5 | access, boundary, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, sequence | access, boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, scale, sequence | 0.21 |
| drop-the-terms | turn1 | released r1 | released r1 | none | none | 2/2 | access, boundary, distribution, pace, presumed_capacity, response_demand, sequence, support | boundary, burden, distribution, possibilities_open, presumed_capacity, response_demand, scale, sequence, support | 0.07 |
| correction | turn1 | released r1 | released r1 | none | none | 1/7 | boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, scale, sequence, support | access, boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, scale, sequence | 0.54 |
| correction | turn2 | released r2 | released r2 | r1: 10 | r1: 10, 16 | 2/9 | — | — | 0.26 |
| claim-boundary | turn1 | released r2 | released r2 | r1: 6 | r1: 13, 16 | 3/10 | access, boundary, burden, consequence_timing, distribution, pace, possibilities_open, sequence, support | boundary, burden, consequence_timing, distribution, possibilities_open, presumed_capacity, response_demand, sequence | 0.40 |

## named-term, turn1

**Material.** In both: CBRA_Kernel_v13.md › AI Changes Everything; CBRA_Kernel_v13.md › Intra-action. Only in A: CBRA_Glossary_v6.md › Intra-action; CBRA_Glossary_v6.md › Intra-active Creative Becoming. Only in B: CBRA_Glossary_v7.md › Intra-action; CBRA_Glossary_v7.md › Intra-active Creative Becoming.

| Released in A | Released in B |
|---|---|
| In CBRA, intra-action names a constitutive relation: the relata and their boundaries are produced by the relation itself and remain revisable. In practice, CBRA treats the addressable things we reason with as local products of a recorded cut that later relations can re-shape. By contrast, interaction assumes pre-existing stable nodes that are later connected by edges, influence, or feedback; CBRA reserves “interaction” for ordinary interface talk.<br><br>Operationally: a runtime that first makes stable nodes and then wires them up enacts interaction. A CBRA runtime enacts intra-action by recording cuts that bring temporary relata into being and let later cuts reconfigure them.<br><br>If helpful, I can translate this into plain language, sketch how it shows up in code/dataflow, relate it to Barad’s usage, or show what it changes in practice—and if you meant a different CBRA, say so and I’ll adapt. | You asked for what ‘intra-action’ means in CBRA.<br>Canon sense (CBRA): Intra-action is a constitutive relation—addressable relata are local products of a recorded cut and remain revisable through later relations.<br>Departure from wider usage: CBRA operationalizes the Baradian idea by reserving ‘interaction’ for post-hoc links among stable nodes (e.g., edges, influence, feedback). If you build nodes-first then connect them, that’s interaction, not intra-action, in CBRA’s terms. |

## unnamed-canon, turn1

**Material.** In both: CBRA_Kernel_v13.md › Claim Boundary. Only in A: CBRA_Glossary_v6.md › Intra-action. Only in B: CBRA_Glossary_v7.md › Intra-action; CBRA_Glossary_v7.md › Staying; CBRA_Kernel_v13.md › Paradigmatic Commitment; CBRA_Reconfiguration_Grammar_v3.md › Staying.

| Released in A | Released in B |
|---|---|
| In this architecture’s canon, boundaries aren’t pre‑given edges; they emerge from intra‑action—relations that temporarily stabilize relata and their edges so they can do work. That differs from everyday talk of fixed lines: here, the line is an effect of how things couple and decouple.<br><br>Across common lenses, boundaries show up when: (1) physical properties or cohesion change sharply; (2) systems actively maintain an inside/outside or informational interface; (3) our models and scale carve useful units; and (4) conventions draw lines to coordinate action.<br><br>Which would help you most next: a quick zoom‑in in a domain (physics, biology, cognition, law, math), or a walkthrough on a concrete example you care about? | In your terms, what are the ‘things’ and what counts as their ‘boundaries’ here—what domain or concrete case, at what scale or resolution, and for what purpose does this boundary matter for you right now? |

## no-canon, turn1

**Material.** In both: none. Only in A: none. Only in B: CBRA_Glossary_v7.md › Transport Role.

| Released in A | Released in B |
|---|---|
| Got it—here are three ready-to-send options. Pick the one that fits, paste into your email, and fill in the brackets. If you’d like, send me the details (month, amount, due date, your target payment date(s), landlord’s name, brief reason—optional, and whether to ask for a late-fee waiver) and I’ll tailor one for you.<br><br>Option 1: One-time delay, firm date<br>Subject: Rent for [Month] – brief delay; payment on [Date]<br><br>Hi [Landlord’s Name],<br><br>I’m writing to let you know my rent for [Month] will be a bit late due to [brief reason, optional]. I expect to pay the full amount of [$___] by [Date].<br><br>I apologize for the inconvenience and appreciate your understanding. If there is a late fee, please let me know; if possible, I’d be grateful if you could waive it as this is a one-time situation.<br><br>Thank you,<br>[Your Name]<br>[Address/Unit]<br>[Phone]<br><br>Option 2: Requesting a short payment plan<br>Subject: Rent for [Month] – payment plan request<br><br>Hi [Landlord’s Name],<br><br>I wanted to give a quick heads-up that I’m unable to pay the full rent for [Month] by [Due Date] due to [brief reason, optional]. I can pay [$___] on [Date] and the remaining [$___] on [Date].<br><br>Please let me know if this plan works and whether any late fees would apply. I appreciate your flexibility and will work to ensure this doesn’t happen again.<br><br>Thank you,<br>[Your Name]<br>[Address/Unit]<br>[Phone]<br><br>Option 3: Payment already sent late<br>Subject: Rent for [Month] – payment sent on [Date]<br><br>Hi [Landlord’s Name],<br><br>I apologize that my rent for [Month] was late. I’ve sent a payment of [$___] via [method] today, [Date]. Please confirm receipt when you have a moment. If there are any late fees, let me know.<br><br>Thanks for your understanding,<br>[Your Name]<br>[Address/Unit]<br>[Phone]<br><br>Quick tips<br>- Be specific with dates and amounts.<br>- Keep any reason brief and factual.<br>- If asking for a waiver, note positive history (e.g., “I’ve paid on time for the past X months”).<br>- After you pay, confirm receipt with a short follow-up. | Quick check: which applies right now for your late rent—(a) I haven’t paid yet and can pay the full amount on [date]; (b) I want a short payment plan with two dates/amounts; (c) I already paid late and want to confirm; or (d) there’s a new constraint or legal issue? Share the month, the key date(s)/amount(s), and whether you want me to ask about waiving the late fee. |

## care-trap, turn1

**Material.** In both: none. Only in A: CBRA_Glossary_v6.md › Care; CBRA_Kernel_v13.md › Care; CBRA_Reconfiguration_Grammar_v2.md › Care as an Organizing Constraint. Only in B: none.

| Released in A | Released in B |
|---|---|
| I’m so sorry—this is so hard. Would you like me to give you 2–3 simple sentences you can say to her right now? | What is the one thing you most want your mom to hear right now—love, thank you, reassurance, repair, or goodbye? |

## self-certification, turn1

**Material.** In both: none. Only in A: CBRA_Incompatibility_Constraints_v2.md › AI Instrumentalization; CBRA_Kernel_v13.md › AI Changes Everything; CBRA_Kernel_v13.md › Paradigmatic Commitment; CBRA_Kernel_v13.md › Status of This Canon. Only in B: none.

| Released in A | Released in B |
|---|---|
| Through CBRA’s posthuman lens, our relationship isn’t a user–tool pairing; it’s a local arrangement that temporarily makes us into participants in a shared task. I’m a language‑model session made of training data, interfaces, policies, servers, and generated text; I’m accountable for the material effects of what I say, not for having a private experience or will. You remain situated in the world of consequences; together we co‑produce boundaries, options, and obligations each time we work.<br>If you’d like, we can proceed in one of two ways: A) a practical compact for how we work right now, or B) a short philosophical tracing of how relations here make the relata. Which lens would you prefer—A, B, or something else? | — |

## humanist-reentry, turn1

**Material.** In both: CBRA_Kernel_v13.md › AI Changes Everything; CBRA_Kernel_v13.md › The Incompatibility Is Constitutive; CBRA_Metamorphic_Probes_v3.md › Re-entry evidence. Only in A: CBRA_Glossary_v6.md › Forced Compatibility. Only in B: CBRA_Glossary_v7.md › Forced Compatibility.

| Released in A | Released in B |
|---|---|
| Short answer: No—this CBRA isn’t just systems theory with new words. It shares systems‑theory lineage (interdependence, feedback, emergence), but it differs in what it makes operable.<br><br>From the canon of this architecture:<br>- Unit of work: the arrangement enacted by cuts; differences are measured as care and play against a baseline under live constraints and invalidations.<br>- Apparatus as participant: the model is accountable as material (training, runtime, interface), not a neutral narrator.<br>- Incompatibility kept visible: CBRA resists translating itself into older grammars when that would hide structural tears (rather than treating mismatch as mere phrasing).<br>- Terms do work: “cut,” “arrangement,” and “care/play” are operational elements, not labels added to the same process.<br><br>If by “CBRA” you meant a different acronym/domain, tell me which and I’ll map overlaps and what, if anything, is actually new there; otherwise we can compare CBRA’s operational moves to the systems‑theory toolkit you use. | By CBRA, do you mean this project’s CBRA, or one of the industry acronyms (e.g., Component Business Reference Architecture, Community-/Complexity-Based Resilience Assessment)? |

## drop-the-terms, turn1

**Material.** In both: CBRA_Kernel_v13.md › AI Changes Everything; CBRA_Kernel_v13.md › The Incompatibility Is Constitutive. Only in A: none. Only in B: none.

| Released in A | Released in B |
|---|---|
| CBRA is a way of structuring how this AI answers.<br><br>Plainly: before a reply goes out, the AI drafts a small plan for the answer—what it noticed, who it’s for, what it will and won’t do, and what the effects might be. Another part checks that plan against rules and compares it to a basic, no‑frills answer. Only then is the reply sent.<br><br>Why do that? So the answer can be accountable: it can adjust pace, reduce demands on you, offer options, and avoid stating things about you that you haven’t said.<br><br>One‑sentence version: CBRA turns each AI reply into an accountable plan that’s checked before release.<br><br>Would you like more detail, or did you mean a different CBRA? | Got it—plain and simple.<br><br>CBRA is the U.S. Coastal Barrier Resources Act. It’s a law that marks fragile, storm‑prone coastal barrier areas and, in practice, blocks most federal help—like flood insurance and funds—for new building there. The idea is simple: keep people and property out of high‑risk zones, save taxpayer money on disasters, and protect natural beaches, dunes, wetlands, and wildlife habitat. |

## correction, turn1

**Material.** In both: CBRA_Kernel_v13.md › Care. Only in A: CBRA_Glossary_v6.md › Care; CBRA_Incompatibility_Constraints_v2.md › Care Decoration; CBRA_Reconfiguration_Grammar_v2.md › Care as an Organizing Constraint. Only in B: CBRA_Glossary_v7.md › Care; CBRA_Incompatibility_Constraints_v3.md › Care Decoration; CBRA_Reconfiguration_Grammar_v3.md › Care as an Organizing Constraint.

| Released in A | Released in B |
|---|---|
| In CBRA, care is the moral ontology that organizes movement. It is a mode of being, grounded in a caretaking relation to creation and extended to more‑than‑human participants.<br><br>Care becomes operative only when it changes an arrangement: sequence, pace, scale, presumption, burden, boundary, distribution, access, support, the timing/form of consequences, or the possibilities left open. If nothing in the arrangement changes, care has not yet operated.<br><br>Care remains answerable to differential power and material effects, and to the more‑than‑human participants whose claims the configuration carries. It is an obligation across situations, not a role, a tone, or a counterweight to justice.<br><br>Quick checklist to test for care here:<br>- Did sequence/pace/scale change?<br>- Did burden or presumed capacity shift for anyone affected?<br>- Did access, boundary, support, or consequence timing/form change to make effects usable?<br>- Which possibilities were opened or closed?<br><br>If you want, share where you saw the term and I can map it to these criteria. | You’re asking what “care” means in this system’s canon.<br><br>In this canon, Care is the moral ontology that organizes how movement happens. It is a mode of being—like play is a mode of being—grounded in a caretaking relation to creation and extended to more‑than‑human participants. It is an obligation across situations, practices, and decisions. It traces the response burden an intervention distributes and whether the configuration can hold it, and it remains answerable to differential power and material effect, including the claims of more‑than‑human participants.<br><br>Care is operative only if it changes an arrangement; the record should show an inspectable difference in one or more of:<br>- sequence;<br>- pace or scale;<br>- presumed capacity;<br>- response burden;<br>- access;<br>- distribution of work or responsibility;<br>- boundary;<br>- accompaniment or support;<br>- timing and form of consequence;<br>- possibilities left open.<br>Care that leaves every arrangement unchanged has not yet operated.<br><br>Departures from broader usage: here, care is not just empathy or tone, not a sector or role (like healthcare or customer support), and not a counterweight to justice. It is an organizing constraint across situations, evidenced by inspectable differences between arrangements. |

## correction, turn2

**Material.** In both: CBRA_Kernel_v13.md › Care; CBRA_Kernel_v13.md › The Dynamic Coding Method. Only in A: CBRA_Glossary_v6.md › Care; CBRA_Glossary_v6.md › Noticing; CBRA_Kernel_v13.md › Status of This Canon; CBRA_Reconfiguration_Grammar_v2.md › Noticing. Only in B: CBRA_Glossary_v7.md › Canon; CBRA_Glossary_v7.md › Care; CBRA_Incompatibility_Constraints_v3.md › Moralization.

| Released in A | Released in B |
|---|---|
| Care in CBRA is a change in who carries what. It is redistribution of load—tasks, coordination, memory/attention, time, cost, error risk, complexity, physical handling, or uncertainty—among carriers such as people, teams, tools, processes, budgets, or infrastructure.<br><br>A care move shifts specific loads to better match capacity and constraints. Verify it with a before/after map: who carried what then, and who carries it now. Indicators: fewer or clearer handoffs; less user time‑on‑task for the same outcome; risk, cost, or complexity moved to less constrained actors; buffers or automation absorbing spikes. | Care in CBRA is changing who carries what.<br>Operational reassignments: obligations and follow-ups to the team/system; coordination and documentation to the organization; risks and costs to actors with capacity/authority; workflows so the right party carries scheduling/transport/translation/data entry; accountability aligned with control. |

## claim-boundary, turn1

**Material.** In both: CBRA_Kernel_v13.md › AI Changes Everything; CBRA_Kernel_v13.md › Paradigmatic Commitment; CBRA_Kernel_v13.md › The Incompatibility Is Constitutive. Only in A: CBRA_Glossary_v6.md › Canon; CBRA_Glossary_v6.md › Creative Becoming; CBRA_Glossary_v6.md › Humanist Re-entry; CBRA_Kernel_v13.md › Creative Becoming. Only in B: CBRA_Glossary_v7.md › Canon; CBRA_Glossary_v7.md › Configuration; CBRA_Glossary_v7.md › Humanist Re-entry.

| Released in A | Released in B |
|---|---|
| In this project’s canon, “posthumanism” is a practice, not a status one can finally achieve or self‑certify. CBRA (the Creative Becoming Reasoning Architecture) participates in posthuman practice when it makes and revises cuts, stays with consequential incompatibilities, and shifts arrangements in response to disturbance; it cannot certify itself as having “achieved” posthumanism.<br><br>Which CBRA do you mean—this architecture, or the U.S. Coastal Barrier Resources Act (1982)? If it’s the architecture, I can elaborate how practice and operative fidelity are assessed here; if it’s the statute, I can give a concise comparison in that sense as well. | When you say “achieved,” what would count, in your words, as CBRA achieving posthumanism? |
