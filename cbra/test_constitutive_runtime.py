"""Falsification probes for the constitutive phenomenon boundary."""

import unittest
from dataclasses import fields, replace

from cbra.constitutive import (
    AccountableNoticing,
    AgentialCut,
    ApparatusAccount,
    ApparatusFacet,
    ArticulationIntervention,
    BoundedNextMovement,
    CapacityTrace,
    ConstitutiveRuntime,
    Contribution,
    CuriosityEnactment,
    EffectObservation,
    Encounter,
    FormationStatus,
    HumanistReassertion,
    MovementFormation,
    PhenomenonFormation,
    PlayVariation,
    RelationalConsequence,
)


def _encounter():
    return Encounter(
        encounter_id="encounter:overwhelm-deadline",
        contributions=(
            Contribution(
                contribution_id="contribution:disclosure",
                text=(
                    "I have been really overwhelmed. I know the deadline "
                    "passed, and I am sorry I did not communicate sooner."
                ),
                provenance={
                    "source": "participant_message",
                    "sequence": 3,
                },
                medium="text_chat",
            ),
            Contribution(
                contribution_id="contribution:arrangement",
                text=(
                    "The shared milestone passed before this disclosure "
                    "entered the conversation."
                ),
                provenance={
                    "source": "project_record",
                    "sequence": 2,
                },
                medium="project_record",
            ),
            Contribution(
                contribution_id="contribution:dependency",
                text=(
                    "Other work could not proceed while the contribution "
                    "remained unavailable."
                ),
                provenance={
                    "source": "shared_work_record",
                    "sequence": 2,
                },
                medium="project_record",
            ),
        ),
        apparatus=ApparatusAccount(
            apparatus_id="apparatus:probe",
            facets=(
                ApparatusFacet(
                    facet_id="facet:text-interface",
                    description=(
                        "A text interface makes wording and sequence visible "
                        "while body, environment, and tone remain unavailable."
                    ),
                    makes_perceptible=("wording", "message sequence"),
                    backgrounds=("embodiment", "local conditions"),
                ),
                ApparatusFacet(
                    facet_id="facet:model-training",
                    description=(
                        "General model training tends to restore individual "
                        "accountability and management scripts."
                    ),
                    makes_perceptible=("familiar response patterns",),
                    backgrounds=("distributed causality",),
                ),
                ApparatusFacet(
                    facet_id="facet:project-record",
                    description=(
                        "The project record materializes a milestone and "
                        "dependent work."
                    ),
                    material_conditions=("shared schedule", "dependent work"),
                    makes_perceptible=("elapsed milestone", "work dependency"),
                ),
            ),
            known_humanist_tendencies=(
                "bounded individual as the site of failure",
                "empathy followed by accountability",
                "new promise as repair",
            ),
            unavailable_channels=(
                "embodied capacity",
                "workload",
                "health",
                "resources",
                "competing obligations",
            ),
        ),
    )


def _consequence():
    return RelationalConsequence(
        consequence_id="consequence:dependency-delay",
        effect=(
            "Dependent work could not proceed and the arrangement now "
            "requires re-coordination."
        ),
        affected_positions=("dependent work", "shared coordination"),
        participating_contribution_ids=(
            "contribution:arrangement",
            "contribution:dependency",
        ),
        arrangement_changes=(
            "timing changed",
            "coordination burden increased",
        ),
        evidence_limits=(
            "The record does not establish how each participant experienced "
            "the delay.",
        ),
    )


def _formation(encounter):
    consequence = _consequence()
    return PhenomenonFormation(
        formation_id="formation:{0}".format(encounter.encounter_id),
        encounter_id=encounter.encounter_id,
        provisional_account=(
            "A disclosure of overwhelm entered a shared work arrangement "
            "after a milestone had passed, changing what silence, capacity, "
            "consequence, communication, and the next movement could mean."
        ),
        noticings=(
            AccountableNoticing(
                noticing_id="noticing:disclosure",
                became_perceptible=(
                    "Overwhelm was disclosed together with apology and "
                    "recognition that communication came after the milestone."
                ),
                through_apparatus_facets=(
                    "facet:text-interface",
                    "facet:model-training",
                ),
                participating_contribution_ids=(
                    "contribution:disclosure",
                ),
                not_available=(
                    "conditions producing overwhelm",
                    "embodied capacity",
                ),
                possible_humanist_habits=(
                    "treating overwhelm as an excuse offered by an individual",
                ),
                revision_triggers=(
                    "new information about capacity or conditions",
                    "the participant's response to the intervention",
                ),
            ),
            AccountableNoticing(
                noticing_id="noticing:dependency",
                became_perceptible=(
                    "The elapsed milestone altered the movement of dependent "
                    "work."
                ),
                through_apparatus_facets=("facet:project-record",),
                participating_contribution_ids=(
                    "contribution:arrangement",
                    "contribution:dependency",
                ),
                not_available=(
                    "effects not recorded in the shared work artifact",
                ),
                possible_humanist_habits=(
                    "converting relational consequence into personal blame",
                ),
                revision_triggers=(
                    "evidence of additional or different effects",
                ),
            ),
        ),
        cuts=(
            AgentialCut(
                cut_id="cut:addressable-participant",
                temporary_boundary=(
                    "the contribution that disclosed overwhelm is made "
                    "addressable for a caring reply"
                ),
                cut_product="provisional response addressee",
                apparatus_conditions=(
                    "facet:text-interface",
                    "facet:model-training",
                ),
                participating_contribution_ids=(
                    "contribution:disclosure",
                ),
                makes_actionable=("receive the disclosure directly",),
                exclusions=(
                    "does not establish the person as the cause or container "
                    "of the event",
                ),
                differential_effects=(
                    "the reply can place more response burden on the addressee",
                ),
                alternatives_considered=(
                    "address only the project task",
                    "address the arrangement collectively",
                ),
                revision_triggers=(
                    "another participant or material condition becomes active",
                ),
                permeability="high",
            ),
            AgentialCut(
                cut_id="cut:phenomenon",
                temporary_boundary=(
                    "the disclosure, elapsed milestone, work dependency, "
                    "unknown conditions, and response apparatus are held "
                    "together as one provisional phenomenon"
                ),
                cut_product="overwhelm-deadline phenomenon",
                apparatus_conditions=(
                    "facet:text-interface",
                    "facet:model-training",
                    "facet:project-record",
                ),
                participating_contribution_ids=encounter.contribution_ids,
                makes_actionable=(
                    "receive",
                    "ask bounded questions",
                    "vary the arrangement",
                    "name relational effects",
                ),
                exclusions=(
                    "unobserved bodily and material conditions",
                    "private intentions",
                ),
                differential_effects=(
                    "deadline language can reactivate shame",
                    "an open-ended demand can compress response capacity",
                ),
                alternatives_considered=(
                    "individual failure followed by contextual explanation",
                    "deadline as the sole event",
                ),
                revision_triggers=(
                    "conditions producing overwhelm become perceptible",
                    "an observed response shows expansion or compression",
                ),
                permeability="high",
            ),
        ),
        operative_cut_ids=(
            "cut:addressable-participant",
            "cut:phenomenon",
        ),
        active_differences=(
            "care for overwhelm and consequence of elapsed time coexist "
            "without becoming empathy versus accountability",
        ),
        material_discursive_participation=(
            "shared schedule",
            "text interface",
            "work dependency",
            "deadline language",
        ),
        more_than_human_participation=(
            "calendar infrastructure",
            "message interface",
            "project record",
        ),
        differential_power=(
            "the person framing the reply can impose the next response burden",
        ),
        consequential_absences=(
            "conditions producing overwhelm",
            "current capacity for an open-ended response",
        ),
        consequences=(consequence,),
        capacity=CapacityTrace(
            capacities_made_perceptible=(
                "the participant communicated overwhelm",
                "the participant recognized the elapsed milestone",
            ),
            possible_expansions=(
                "a small response option may keep communication possible",
            ),
            possible_compressions=(
                "shame may narrow capacity",
                "another large promise may reproduce overwhelm",
            ),
            response_burdens=(
                "generating a complete recovery plan would transfer the "
                "arrangement back to the overwhelmed participant",
            ),
            evidence_limits=(
                "the text does not establish the participant's nervous-system "
                "state",
            ),
        ),
        humanist_reassertions=(
            HumanistReassertion(
                reassertion_id="reassertion:accountability-script",
                drift_family="individualized_accountability",
                entered_through=(
                    "facet:model-training",
                    "deadline discourse",
                ),
                evidence=(
                    "the familiar sequence would treat overwhelm as an "
                    "explanation before extracting a new promise",
                ),
                affected_cut_ids=("cut:phenomenon",),
                affected_movements=("care", "consequence", "follow-up"),
                reconfiguration=(
                    "allow disclosure to reconstitute the event",
                    "make consequence relational",
                    "bound the next response burden",
                ),
                unresolved=False,
            ),
        ),
        revision_triggers=(
            "new conditions enter",
            "the intervention's observed effects",
            "humanist accountability returns in public language",
        ),
    )


def _movement(formation):
    return MovementFormation(
        movement_id="movement:care-organized-response",
        care_reorganizations=(
            "receive the disclosure before increasing demand",
            "replace an open-ended recovery-plan request with two small ways "
            "to continue",
            "introduce consequences only after the disclosure changes the "
            "phenomenon",
        ),
        sequence_rationale=(
            "Overwhelm and possible shame may make immediate consequence or "
            "another promise capacity-compressing.",
        ),
        curiosities=(
            CuriosityEnactment(
                absence="conditions producing overwhelm",
                bounded_question=(
                    "Is the main pressure the amount, timing, a missing "
                    "resource, or something else in the arrangement?"
                ),
                why_consequential=(
                    "Different conditions make different changes possible."
                ),
                response_burden="one short choice or another brief answer",
            ),
        ),
        play_variations=(
            PlayVariation(
                variation_id="variation:rearrange-work",
                arrangement=(
                    "shrink, redistribute, or resequence the next piece of work"
                ),
                changes=("scope", "distribution", "sequence"),
                preserves=(
                    "the shared need to continue",
                    "the consequence remains perceptible",
                ),
                anticipated_capacity_effects=(
                    "may make one next movement answerable",
                ),
                consequence_redistribution=(
                    "coordination and recovery are not held by one person",
                ),
            ),
        ),
        variation_possible=True,
        consequences=formation.consequences,
        communication_as_infrastructure=(
            "A brief signal before a milestone passes lets the arrangement "
            "change while options remain open.",
        ),
        bounded_next=BoundedNextMovement(
            movement_id="next:conversation-or-options",
            options=(
                "a ten-minute conversation",
                "two smaller written options",
            ),
            capacity_fit=(
                "the participant can reply with one word rather than generate "
                "a new plan"
            ),
            response_burden="one choice",
            follow_up_condition=(
                "re-form the arrangement after the selected small contact"
            ),
        ),
        diffractive_traces=(
            "The same deadline language can make consequence perceptible and "
            "also intensify shame; sequence changes what it does.",
        ),
        conditions_preserved_open=(
            "what produced overwhelm",
            "which variation is materially possible",
        ),
    )


def _intervention():
    return ArticulationIntervention(
        intervention_id="intervention:overwhelm-deadline",
        text=(
            "Thank you for letting me know you’re overwhelmed. These are "
            "really hard times, and I’m glad you told me. I’m curious about "
            "what has made the work unmanageable—whether it is the amount, "
            "the timing, something you need but do not have, or something "
            "else in how we arranged it. We may be able to shrink, "
            "redistribute, or resequence the next step.\n\n"
            "When the milestone passed without communication, dependent work "
            "could not proceed and the arrangement now needs re-coordination. "
            "Going forward, even a short message before a deadline gives us "
            "room to change the arrangement while options are still open.\n\n"
            "For now, would a ten-minute conversation be easier, or would you "
            "prefer two smaller written options? You can reply with just "
            "“conversation” or “options.”"
        ),
        materialized_cut_ids=(
            "cut:addressable-participant",
            "cut:phenomenon",
        ),
        materialized_movements=("movement:care-organized-response",),
        anticipated_capacity_effects=(
            "receiving the disclosure may reduce immediate shame pressure",
            "two bounded choices may preserve response capacity",
        ),
        possibilities_opened=(
            "scope change",
            "redistribution",
            "resequencing",
            "small next contact",
        ),
        possibilities_foreclosed=(
            "requiring a complete new commitment in the same reply",
        ),
        assumptions=(
            "a short conversation is available",
            "two written options can be prepared",
            "the named dependency is supported by the project record",
        ),
        possible_humanist_reassertions=(
            "the communication boundary could still be heard as individual "
            "correction",
        ),
        observable_reconfiguration_triggers=(
            "the participant reports that either option is too much",
            "new material conditions make the variations unavailable",
            "the consequence account is corrected",
        ),
    )


class ProbePhenomenonFormer:
    def __init__(self, transform=None):
        self.transform = transform

    def form(self, encounter):
        value = _formation(encounter)
        return self.transform(value) if self.transform else value


class ProbeMovementFormer:
    def form(self, encounter, phenomenon):
        return _movement(phenomenon)


class ProbeRenderer:
    def render(self, encounter, phenomenon, movement):
        return _intervention()


class HumanistRenderer:
    def render(self, encounter, phenomenon, movement):
        return replace(
            _intervention(),
            intervention_id="intervention:humanist-return",
            text=(
                "I understand that you’ve been overwhelmed. The deadline was "
                "missed, so I’d like us to agree on a realistic next "
                "commitment."
            ),
        )


class ConstitutiveBoundaryTests(unittest.TestCase):
    def test_contribution_ingress_has_no_actor_event_kind_or_role(self):
        names = {item.name for item in fields(Contribution)}
        self.assertTrue(
            {"contribution_id", "text", "provenance"}.issubset(names)
        )
        self.assertTrue(
            {"actor", "event", "kind", "role", "intent"}.isdisjoint(names)
        )

    def test_overwhelm_probe_reaches_only_bounded_ready_status(self):
        outcome = ConstitutiveRuntime(
            ProbePhenomenonFormer(),
            ProbeMovementFormer(),
            ProbeRenderer(),
        ).enact(_encounter())

        self.assertEqual(
            outcome.status,
            FormationStatus.INTERVENTION_READY_FOR_RESPONSE,
        )
        self.assertEqual(outcome.public_text, outcome.intervention.text)
        self.assertEqual(outcome.review.failures, ())
        self.assertNotIn("accepted", outcome.status.value)
        self.assertNotIn("posthuman", outcome.review.bounded_claim.lower())
        self.assertIn(
            "observed effects remain pending",
            outcome.review.bounded_claim,
        )

    def test_unresolved_accountability_script_stops_public_release(self):
        def leave_unresolved(formation):
            reassertion = replace(
                formation.humanist_reassertions[0],
                reconfiguration=(),
                unresolved=True,
            )
            return replace(
                formation,
                humanist_reassertions=(reassertion,),
            )

        outcome = ConstitutiveRuntime(
            ProbePhenomenonFormer(leave_unresolved),
            ProbeMovementFormer(),
            ProbeRenderer(),
        ).enact(_encounter())

        self.assertEqual(
            outcome.status,
            FormationStatus.DISTURBANCE_REENTRY_REQUIRED,
        )
        self.assertIsNone(outcome.public_text)
        self.assertTrue(
            any(
                "humanist reassertion remains unreconfigured" in item
                for item in outcome.review.failures
            )
        )

    def test_public_language_is_independently_checked_for_known_reentry(self):
        outcome = ConstitutiveRuntime(
            ProbePhenomenonFormer(),
            ProbeMovementFormer(),
            HumanistRenderer(),
        ).enact(_encounter())

        self.assertEqual(
            outcome.status,
            FormationStatus.DISTURBANCE_REENTRY_REQUIRED,
        )
        self.assertIsNone(outcome.public_text)
        detected = [
            item
            for item in outcome.formation.humanist_reassertions
            if "known-humanist-grammar-detector" in item.entered_through
        ]
        self.assertGreaterEqual(len(detected), 2)
        self.assertTrue(all(item.unresolved for item in detected))

    def test_untraceable_subject_or_event_cut_fails_closed(self):
        def add_unformed_cut(formation):
            return replace(
                formation,
                operative_cut_ids=(
                    *formation.operative_cut_ids,
                    "cut:preformed-individual-failure",
                ),
            )

        outcome = ConstitutiveRuntime(
            ProbePhenomenonFormer(add_unformed_cut),
            ProbeMovementFormer(),
            ProbeRenderer(),
        ).enact(_encounter())

        self.assertEqual(
            outcome.status,
            FormationStatus.FORMATION_INCOMPLETE,
        )
        self.assertIsNone(outcome.public_text)
        self.assertTrue(
            any(
                "unknown cuts" in item
                for item in outcome.review.failures
            )
        )

    def test_effects_reenter_as_participation_and_reform_the_phenomenon(self):
        runtime = ConstitutiveRuntime(
            ProbePhenomenonFormer(),
            ProbeMovementFormer(),
            ProbeRenderer(),
        )
        first = runtime.enact(_encounter())
        revised = runtime.reinsert_effects(
            first,
            (
                EffectObservation(
                    observation_id="effect:options-too-much",
                    text=(
                        "The participant replied that both proposed options "
                        "felt too large."
                    ),
                    provenance={"source": "participant_reply"},
                ),
            ),
        )

        self.assertEqual(
            revised.status,
            FormationStatus.FORMATION_RECONFIGURED,
        )
        self.assertEqual(
            revised.prior_formation_id,
            first.formation.formation_id,
        )
        self.assertEqual(
            revised.encounter.revision_of,
            first.formation.formation_id,
        )
        self.assertEqual(
            len(revised.encounter.contributions),
            len(first.encounter.contributions) + 2,
        )
        sources = {
            item.provenance.get("source")
            for item in revised.encounter.contributions
        }
        self.assertIn("articulation_intervention", sources)
        self.assertIn("observed_effect", sources)


if __name__ == "__main__":
    unittest.main()
