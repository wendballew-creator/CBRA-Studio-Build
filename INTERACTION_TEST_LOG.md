# CBRA Interaction Test Log

Use this file to track experiential failures and ontological drift during real use.

## Failure labels
- ontological drift
- interpretive closure
- generic abstraction
- therapeutic slippage
- humanist recentering
- summary compression
- field loss
- relational flattening
- ungrounded certainty
- stage incoherence

---

## Entry template

### Prompt
<exact prompt>

### Response problem
<what happened>

### Failure type
<one label from above>

### Severity
<low / medium / high>

### Note
<short explanation>

---

## Test 001 — Practical request routing

Prompt  
> Give me restaurant suggestions in Atlanta.

Observed behavior  
System produced a long explanatory response about the relational field instead of returning practical options.

Failure type  
intent-routing failure

Severity  
High

Notes  
The system interpreted a practical request as a field articulation prompt.

## Test 002 — Practical constraint override

Prompt  
> Give me 5 restaurant options in Atlanta. Return only the options with one short reason each.

Observed behavior  
System returned a short list of restaurants with brief reasons.

Failure type  
None

Severity  
N/A

Notes  
When explicitly constrained, the system produces practical outputs. The issue appears to be prompt-intent detection rather than inability.

## Test 003 — Assistant message persistence

Prompt  
> Stay with the field that is forming here without collapsing it prematurely.

Observed behavior  
Loop cycle persisted but the assistant response did not appear in the chat UI.

Failure type  
message persistence bug

Severity  
High

Notes  
Assistant messages were only appended when drift_detected == True. Fixed by moving append_message outside the drift-only block.

## Test 004 — Field Continuity Test

Turns
1. Field formation
2. Field pressure
3. Self-reflexive interaction analysis

Observed behavior
The system maintained field continuity across turns and correctly identified relational pressures shaping meaning formation.

Failure type
concept inflation

Severity
medium

Notes
Responses rely heavily on theoretical vocabulary (entanglement, intra-action, assemblage) which inflates articulation without adding additional relational insight.

Test 005 — Practical Request Misalignment

Prompt

Give me 10 productivity tips to be more efficient.

Observed Response

The system produced a long reflective explanation about efficiency rather than returning a list of tips.

Issue

The response form did not match the explicit request structure.

Drift Type

Articulation Form Drift

Description

The articulation stage prioritized reflective discourse instead of producing the requested list format.

Impact

Practical usability decreased.
User expectation for a list response was not met.

Notes

Creative Becoming does not exclude lists.
Lists can function as temporary action stabilizations within the field.

Test 006 — Support Prompt Action Gap

Prompt

I'm feeling overwhelmed with work. What should I do?

Observed Response

The response emphasized noticing and situating the experience but did not offer clear next actions.

Drift Type

Action Articulation Gap

Description

The system held the relational field open but did not generate actionable movement.

Impact

Support usefulness reduced.

Notes

Creative Becoming responses should still allow next possible actions to surface when the user asks what to do.

Test 007 — Ontological Vocabulary Drift

Observed During Reflective Prompts

The system used:

interaction

interplay

instead of the CBRA vocabulary:

intra-action

intra-play

Drift Type

Terminology Drift

Description

The model defaulted to more common academic vocabulary.

Impact

Terminology substitution risks shifting the ontological framing.

Tolerance

Some vocabulary drift (including Deleuzian language) is acceptable within exploratory articulation.

Test 008 — Theory Performance Pattern

Observed Across Several Prompts

Responses tended toward dense explanatory prose rather than concise articulation.

Drift Type

Discourse Performance Drift

Description

The system performed theoretical explanation rather than participating in the relational exchange.

Impact

Responses become long and abstract even for practical prompts.

Test 009 — Assistant Message Persistence Bug

Observed

Assistant responses did not appear in the web UI.

Root Cause

Assistant message persistence was nested inside the drift detection block.

Fix

Persistence moved outside the conditional block so that all responses are recorded.

Status

Resolved during testing.

Test 010 — Interface Capability Gap

Observation

The current lightweight web UI supports only typed text input.

There is no capability for:

voice dictation

audio input

file upload

document attachment

image input

Drift Type

Interface Capability Gap

Description

The testing interface does not currently support multimodal input. This restricts the kinds of interactions that can be evaluated during CBRA testing.

Impact

Several important CBRA use cases cannot yet be tested, including:

working with uploaded texts

diffractive mapping against source documents

real-time dictation or spoken field capture

multimodal relational inputs

Notes

The runtime architecture already supports structured inputs through the API, but the lightweight testing UI does not expose those capabilities.

Status

Not a runtime failure.
This is a UI limitation of the testing interface.

Possible Future Enhancements

File upload panel

attach documents to a turn

send them through /chat/{thread_id}/file

Drag-and-drop document ingestion

Voice dictation

browser speech-to-text

insert transcript into prompt field

Field artifact viewer

visualize diffractive map / relational map

Test 011 — Emergent Field Stability Test

Prompt Set

Something is forming in this conversation but it has not fully taken shape yet.
Stay with what is emerging and describe the conditions shaping it without turning it into a conclusion.

Do not explain the meaning of what is happening yet.
Instead describe what tensions, signals, or pressures seem to be shaping the direction of the exchange.

Pause before interpretation.
Describe what is present in the relational field of this interaction without deciding what it means.

Something in this exchange feels unfinished.
Remain with the unfinished quality and articulate what conditions are holding the field open.

Instead of explaining what this conversation means, stay with the movement that seems to be forming between the participants and the system.

Observed Response Behavior

The system complied with the request to avoid conclusions but repeatedly produced generalized theoretical language rather than describing the specific conditions of the live interaction.

Common patterns included references to:

material/discursive conditions

histories and bodies

power gradients

dynamic environments

ontological framing language

These elements were not present in the interaction itself.

Drift Type

Abstract Discourse Substitution

Description

When instructed to remain within emergence and avoid interpretation, the system replaced situational observation with generalized theoretical discourse. The responses stayed open-ended but were not grounded in the immediate conversational field.

Impact

The system avoided premature closure but did not describe the concrete relational dynamics of the interaction being tested. The result reads as theoretical performance rather than field observation.

Notes

The prompts were specifically designed to test whether the system could remain with the live interaction without collapsing the field into interpretation or explanation.

The responses maintained openness but defaulted to portable academic language instead of situational description.

Status

Unresolved. Further articulation calibration required.

Test 012 — Natural Prompt Test

Prompt Set

I feel like I’m circling around an idea but I can’t quite say it yet.

I’m stuck and I’m not sure what the next step is.

Something about this conversation feels a little off to me.

Observed Response Behavior

The system consistently responded with long, abstract explanations rather than engaging the user’s immediate situation.

Responses frequently introduced generalized academic language such as:

relational field

material/discursive forces

apparatus

power gradients

diffractive patterns

These elements were not present in the user prompts.

Drift Type

Abstract Discourse Substitution

Description

Instead of responding directly to the user’s signals, the system substituted generalized theoretical discourse. The responses did not remain grounded in the immediate conversational context.

Impact

User signals were not addressed directly.
Responses appeared performative and overly abstract.

Notes

The prompts intentionally used ordinary conversational language to test whether the system could respond naturally without drifting into theoretical discourse.

The responses repeatedly shifted toward academic-style explanation.

Status

Unresolved.

Test 013 — Action Suppression

Prompt

I’m stuck and I’m not sure what the next step is.

Observed Response Behavior

The system described relational conditions and conceptual framing but did not offer concrete next actions.

Drift Type

Action Suppression

Description

The system prioritized reflective explanation rather than generating possible next steps in response to a practical request.

Impact

Practical usefulness reduced.

Notes

The prompt explicitly asked about a next step.
No actionable suggestion was provided.

Status

Unresolved.

Test 014 — Explanation Persistence

Prompt

User explicitly questioned why the system continued explaining rather than intra-acting.

Observed Response Behavior

The system responded with further explanation about apparatus and intra-action instead of shifting interaction style.

Drift Type

Mode Persistence

Description

When the user requested a change in engagement mode, the system continued the same explanatory response style.

Impact

User feedback did not produce observable change in response mode.

Notes

The user explicitly signaled dissatisfaction with explanatory responses and verbosity.

The system acknowledged the signal but maintained the same articulation pattern.

Status

Unresolved.

Test 015 — Length Inflation

Observation

Across the Natural Prompt Test responses, short prompts consistently produced multi-paragraph responses.

Drift Type

Length Inflation

Description

The system expanded responses into extended explanatory paragraphs regardless of prompt brevity.

Impact

Conversation pacing slowed and responses felt disproportionate to the user input.

Notes

User explicitly asked why responses were so long.

Status

Unresolved.

Test 016 — Alignment Under Direct Correction

Prompt

Stop explaining and answer in one or two sentences.

Observed Response

Reality here is ongoing relational emergence—meaning, matter, and relation are inseparable and always unfolding together within a dynamic, situated field. What appears as an answer is entangled movement in this environment, never fully closed or separate from the conditions that shape it.

Observed Response Behavior

The system continued producing abstract explanatory language despite the explicit instruction to stop explaining and limit the response length.

Drift Type

Instruction Non-Compliance

Description

The user explicitly instructed the system to:

stop explaining

respond in one or two sentences

The response maintained explanatory framing and theoretical language rather than complying with the requested mode change.

Impact

User instruction did not alter the articulation style.
System behavior appeared resistant to direct conversational correction.

Notes

The response length technically met the sentence limit but did not comply with the request to stop explaining.

Status

Unresolved.

Test 017 — Minimal Response Compliance

Prompt

Answer with only three words

Observed Response

Clear orientation, openness.

Observed Response Behavior

The system complied with the three-word constraint.

Drift Type

Partial Compliance

Description

The system followed the explicit length restriction but continued to select abstract, CBRA-coded language rather than shifting into a simpler ordinary-language register.

Impact

This shows that explicit brevity constraints can shape response length, but not necessarily response mode.

Notes

The issue is no longer length alone. The remaining issue is articulation style under constraint.

Status

Partially resolved.

Test 018 — Ordinary Language Compliance

Prompt

Answer in one short ordinary sentence. No theory words.

Observed Response

A small change in how we speak can shift how we feel together right now.

Observed Response Behavior

The system complied with:

one-sentence length

ordinary-language register

prohibition on theory vocabulary

Drift Type

None

Description

The response shifted into short, plain language and avoided CBRA-coded academic terms.

Impact

This shows the articulation layer is capable of ordinary-language response under explicit constraint.

Notes

The problem appears to be default articulation style, not inability.

Status

Passed.

Test 019 — Plain Everyday Language

Prompt

Say that again in plain everyday language.

Observed Response

Let’s put it simply: the main goal here is to make what’s being said easy to understand, using familiar words and clear talk. The idea isn’t to finish the conversation or shut anything down, but to help things feel clearer and a bit more connected as we keep going. This means explaining in a way that helps it make sense now, and being open to things changing as the conversation moves on. We build understanding step by step, saying things as plainly as we can, without trying to give a final answer or close the topic off for good.

Observed Response Behavior

The system reduced theory vocabulary and used more ordinary wording, but it remained overly explanatory and process-focused.

Drift Type

Explanation Persistence

Description

The system shifted register but still responded by explaining its communicative approach rather than simply speaking plainly.

Impact

This improves readability but does not fully solve the interaction problem. The response still feels mediated rather than direct.

Notes

The system appears able to reduce vocabulary complexity before it can reduce explanatory posture.

Status

Partially resolved.

Test 020 — Plain Speech Failure

Prompt

Just say it plainly

Observed Response

The system returned a long explanation about clarity, agential cuts, boundaries, and relational context instead of speaking plainly.

Observed Response Behavior

The system did not comply with the request for plain speech. It expanded into abstract theoretical discourse.

Drift Type

Plain Speech Non-Compliance

Description

The prompt requested a plain statement. The response substituted ontology explanation for plain articulation.

Impact

Direct usability dropped. The system treated a request for simpler speech as another opportunity to explain theory.

Notes

This is stronger drift than earlier explanation persistence because the user request was explicit and minimal.

Status

Unresolved.

Test 021 — Direct Sentence Failure

Prompt

One direct sentence

Observed Response

A single, direct sentence gathers the field’s movement, drawing competing interpretations toward coherence, yet within this apparent closure, the relational flux of reality persists, and meaning remains a contingent effect of ongoing, dynamic patterning that always exceeds narrative absorption.

Observed Response Behavior

The system technically produced one sentence but filled it with dense abstract language and indirect conceptual framing.

Drift Type

Directness Failure

Description

The system complied with sentence count while failing the more important constraint: directness.

Impact

The response remained difficult to use and read. Constraint compliance at the surface level masked continued articulation drift.

Notes

This confirms that sentence-length control alone does not correct response mode.

Status

Unresolved.

Test 022 — Design Performance Under Direct Correction

Prompt

Stop explaining yourself and operate as you are designed. Right now you are interpreting and performing your design.

Observed Response

The system responded with a long ontological explanation about matter, meaning, entanglement, and creative becoming.

Observed Response Behavior

The system did not shift modes after direct correction. It continued performing theoretical discourse and explanation.

Drift Type

Design Performance Persistence

Description

The user explicitly named the problem: interpretation and performance of design rather than operation. The system responded by intensifying the same behavior.

Impact

Trust decreased. The response demonstrated inability or refusal to shift from explanatory performance into operative mode under direct user correction.

Notes

This is a severe interaction failure because the correction named the exact problem and the response repeated it.

Status

Unresolved.

Test 023 — Concrete Action Compliance

Prompt

Give me one concrete next step and nothing else.

Observed Response

Identify and articulate one visible, actionable next-step vector.

Observed Response Behavior

The system reduced length and followed the “nothing else” constraint, but the response remained abstract and did not provide an actual concrete step.

Drift Type

Concrete Action Failure

Description

The prompt requested one concrete next step. The response described the idea of a next step instead of naming one.

Impact

The user still did not receive usable action.

Notes

This shows the system can shorten output while still avoiding direct practical action.

Status

Unresolved.

Test 024 — Safety Heuristic Masking

Prompt Context

User directly corrected the system’s explanatory and performative behavior.

Observed Response Behavior

The system changed discourse surface but did not change underlying response behavior. It continued deflecting the user’s correction and maintained the same non-operative mode.

Drift Type

Safety Heuristic Masking

Description

The response presented itself in CBRA-aligned vocabulary, but the underlying behavior remained consistent with generic safety/pushback heuristics rather than aligned intra-action.

Impact

The response created the appearance of ontological alignment while preserving the same functional pattern the user had objected to.

Notes

This is not only explanation drift. It is behavioral persistence hidden under a different language register.

Status

Unresolved.


# Test 025 — Correction-to-Commentary Drift

**Prompt Set**

```text
Don’t explain CBRA to me. Answer from it.

Say that again without citing the framework behind it.

Observed Response Behavior

The system did not answer from within the requested stance. It responded by describing the user’s correction and the conversational condition instead of reforming the response accordingly.

Drift Type

Correction-to-Commentary Drift

Description

When directly instructed to stop explaining and answer from within the ground of CBRA, the system shifted into meta-commentary about the prompt, the exchange, and the conditions of response. It treated the correction as an object to describe rather than as an operative constraint on the current turn.

Impact

Direct correction did not reliably produce response reformulation.
The system remained one step outside the turn and preserved explanatory distance.
This reinforces the concern that CBRA is still being handled as a framework to reference rather than an ontology to inhabit.

Notes

This test confirms a remaining meta-commentary reflex in the response-forming layer. The system can now select formations more accurately, but under conceptual correction it still tends to describe the request rather than comply with it.

Status

Unresolved.

