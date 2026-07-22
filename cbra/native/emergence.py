"""Enact emergent phenomena from the post-update field configuration."""

from __future__ import annotations

from hashlib import sha1
from typing import Dict, List, Set, Tuple

from .hypotheses import RuntimeHypotheses
from .models import EmergentPhenomenon, FieldState, Relation


def _stable_id(prefix: str, *parts: str) -> str:
    body = "|".join(str(part) for part in parts)
    return "{0}:{1}".format(prefix, sha1(body.encode("utf-8")).hexdigest()[:14])


def _connected_relational_components(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> List[Tuple[List[str], List[Relation]]]:
    active_ids = {
        item.stream_id for item in state.streams if item.active
    }
    adjacency: Dict[str, Set[str]] = {
        stream_id: set() for stream_id in active_ids
    }
    relations_by_id: Dict[str, Relation] = {}
    for relation in state.relations:
        if not relation.active:
            continue
        if relation.mutuality < hypotheses.emergence_relation_floor:
            continue
        if relation.left_id not in active_ids or relation.right_id not in active_ids:
            continue
        adjacency[relation.left_id].add(relation.right_id)
        adjacency[relation.right_id].add(relation.left_id)
        relations_by_id[relation.relation_id] = relation

    components: List[Tuple[List[str], List[Relation]]] = []
    unseen = set(active_ids)
    while unseen:
        seed = min(unseen)
        stack = [seed]
        members: Set[str] = set()
        while stack:
            current = stack.pop()
            if current in members:
                continue
            members.add(current)
            unseen.discard(current)
            stack.extend(sorted(adjacency[current] - members, reverse=True))

        if len(members) < 2:
            continue
        component_relations = [
            relation
            for relation in relations_by_id.values()
            if relation.left_id in members and relation.right_id in members
        ]
        if component_relations:
            components.append((sorted(members), component_relations))
    return components


def emerge_phenomena(
    state: FieldState,
    hypotheses: RuntimeHypotheses,
) -> List[EmergentPhenomenon]:
    """Produce every current relational constellation without ranking them."""
    by_id = {item.stream_id: item for item in state.streams}
    phenomena: List[EmergentPhenomenon] = []
    for stream_ids, relations in _connected_relational_components(
        state,
        hypotheses,
    ):
        strength = sum(item.mutuality for item in relations) / len(relations)
        resonance = sum(item.resonance for item in relations) / len(relations)
        difference = sum(item.difference for item in relations) / len(relations)
        kinds = sorted({by_id[item_id].kind for item_id in stream_ids})
        phenomenon_id = _stable_id(
            "phenomenon",
            state.field_id,
            str(state.timestep),
            *stream_ids,
        )
        phenomena.append(
            EmergentPhenomenon(
                phenomenon_id=phenomenon_id,
                stream_ids=stream_ids,
                relation_ids=sorted(item.relation_id for item in relations),
                qualities={
                    "relational_strength": strength,
                    "resonance": resonance,
                    "difference": difference,
                },
                timestep=state.timestep,
                description="Relational constellation across {0}.".format(
                    ", ".join(kinds)
                ),
            )
        )

    known_ids = {item.phenomenon_id for item in state.phenomena}
    for phenomenon in phenomena:
        if phenomenon.phenomenon_id not in known_ids:
            state.phenomena.append(phenomenon)
            known_ids.add(phenomenon.phenomenon_id)
    state.current_phenomenon_ids = sorted(
        item.phenomenon_id for item in phenomena
    )
    return phenomena
