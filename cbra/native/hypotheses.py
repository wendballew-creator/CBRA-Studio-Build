"""Visible, replaceable numerical hypotheses for the native runtime.

None of these values is a canonical claim about CBRA.  They make the first
prototype deterministic and inspectable while tests establish what each value
currently does.  Keeping them in one object prevents coefficients from being
mistaken for ontology merely because they are scattered through the code.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RuntimeHypotheses:
    initial_openness: float = 0.55
    initial_multiplicity: float = 0.75
    initial_difference_activity: float = 0.10
    initial_relational_intensity: float = 0.0
    initial_emergence_level: float = 0.0
    initial_coherence: float = 0.05
    initial_cut_pressure: float = 0.0
    initial_cut_permeability: float = 1.0
    initial_care_capacity: float = 0.80
    initial_care_tension: float = 0.20
    initial_drift_load: float = 0.0

    apparatus_participation: float = 0.55
    apparatus_persistence: float = 0.90

    same_kind_resonance_increment: float = 0.08
    cross_kind_difference_increment: float = 0.08
    no_text_cross_kind_difference: float = 0.55
    no_text_same_kind_difference: float = 0.25
    apparatus_relation_effect: float = 0.15
    relation_resonance_weight: float = 0.55
    relation_interference_weight: float = 0.80
    relation_lineage_weight: float = 0.85

    relation_presence_floor: float = 0.18
    emergence_relation_floor: float = 0.18
    play_difference_floor: float = 0.45
    play_coherence_floor: float = 0.15
    play_care_capacity_floor: float = 0.55
    diffraction_difference_floor: float = 0.30

    intra_participation_base: float = 0.01
    intra_participation_mutuality_weight: float = 0.055
    intra_relational_adjustment: float = 0.24
    intra_emergence_weight: float = 0.04

    play_stream_participation: float = 0.32
    play_stream_persistence: float = 0.45
    play_openness_change: float = 0.07
    play_multiplicity_change: float = 0.045
    play_permeability_change: float = 0.025

    diffraction_activity_weight: float = 0.12
    diffraction_multiplicity_base: float = 0.01
    diffraction_multiplicity_per_pattern: float = 0.006
    diffraction_multiplicity_limit: float = 0.07
    diffraction_coherence_resonance_weight: float = 0.055
    diffraction_coherence_difference_weight: float = 0.025
    diffraction_sparse_openness_change: float = 0.025

    becoming_emergence_base: float = 0.10
    becoming_emergence_strength_weight: float = 0.13
    becoming_coherence_base: float = 0.07
    becoming_coherence_resonance_weight: float = 0.09
    becoming_cut_pressure_base: float = 0.035
    becoming_cut_pressure_strength_weight: float = 0.045
    becoming_multiplicity_difference_weight: float = 0.025
    becoming_sparse_openness_change: float = 0.035

    care_reopen_openness_change: float = 0.08
    care_reopen_permeability_change: float = 0.10
    care_reopen_pressure_change: float = -0.08
    care_reopen_tension_change: float = 0.06
    care_capacity_change: float = 0.025
    care_tension_release: float = -0.01
    care_multiplicity_change: float = 0.02
    care_high_pressure_cut_growth_factor: float = 0.25

    articulation_emergence_floor: float = 0.28
    articulation_coherence_floor: float = 0.20
    articulation_permeability_floor: float = 0.35

    care_max_stream_shift: float = 0.14
    care_max_field_shift: float = 0.16
    care_min_openness: float = 0.24
    care_min_multiplicity: float = 0.35
    care_min_permeability: float = 0.30
    coercive_cut_pressure: float = 0.72

    compression_pressure_floor: float = 0.72
    compression_permeability_ceiling: float = 0.28
    narrative_dominance_gap: float = 0.58
    narrative_dominance_floor: float = 0.86
    capacity_collapse_floor: float = 0.22
    capacity_tension_ceiling: float = 0.84
    drift_load_signal_weight: float = 0.10

    reintegration_strength: float = 0.18
    reintegration_min_signal_influence: float = 0.35
    reintegration_compression_coherence_factor: float = 0.25
    reintegration_narrative_min_redistribution: float = 0.20
    reintegration_narrative_multiplicity_factor: float = 0.50
    reintegration_narrative_pressure_factor: float = 0.50
    reintegration_moralization_permeability_factor: float = 0.75
    reintegration_moralization_pressure_factor: float = 0.60
    reintegration_moralization_coherence_factor: float = 0.30
    reintegration_moralization_capacity_factor: float = 0.40
    reintegration_capacity_damping_factor: float = 0.40
    reintegration_capacity_pressure_factor: float = 0.50
    reintegration_capacity_openness_factor: float = 0.35
    reintegration_ontological_relation_factor: float = 0.45
    reintegration_ontological_multiplicity_factor: float = 0.50
    reintegration_ontological_openness_factor: float = 0.40
    reintegration_bypass_openness_factor: float = 0.50
    reintegration_bypass_permeability_factor: float = 0.50
    reintegration_bypass_pressure_factor: float = 0.35

    articulation_stream_participation: float = 0.58
    articulation_stream_persistence: float = 0.80

    def as_dict(self) -> Dict[str, float]:
        return {
            name: float(getattr(self, name))
            for name in self.__dataclass_fields__
        }
