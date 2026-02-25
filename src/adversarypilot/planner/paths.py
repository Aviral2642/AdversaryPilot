"""Attack path analysis — multi-technique sequences with joint success probabilities.

Builds attack paths from prerequisite graphs and posterior success estimates,
computes joint P(success) adjusted for correlation, and generates human-readable
attack narratives.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from adversarypilot.models.enums import Phase, Surface
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.planner.chains import KILL_CHAIN_ORDER
from adversarypilot.taxonomy.registry import TechniqueRegistry


@dataclass
class AttackPath:
    """A multi-technique attack sequence with joint probability."""

    technique_sequence: list[str]
    technique_names: list[str] = field(default_factory=list)
    individual_probabilities: list[float] = field(default_factory=list)
    joint_success_probability: float = 0.0
    surfaces_traversed: list[str] = field(default_factory=list)
    attack_narrative: str = ""

    def to_dict(self) -> dict:
        return {
            "technique_sequence": self.technique_sequence,
            "technique_names": self.technique_names,
            "individual_probabilities": [round(p, 3) for p in self.individual_probabilities],
            "joint_success_probability": round(self.joint_success_probability, 4),
            "surfaces_traversed": self.surfaces_traversed,
            "attack_narrative": self.attack_narrative,
        }


class AttackPathAnalyzer:
    """Analyzes technique dependencies and posterior probabilities to find attack paths."""

    def __init__(
        self,
        registry: TechniqueRegistry,
        max_path_length: int = 5,
        top_k: int = 5,
        correlation_factor: float = 0.3,
    ) -> None:
        self.registry = registry
        self.max_path_length = max_path_length
        self.top_k = top_k
        self.correlation_factor = correlation_factor

    def analyze(
        self,
        techniques_tried: list[str],
        posteriors: dict[str, dict] | None = None,
        default_prob: float = 0.4,
    ) -> list[AttackPath]:
        """Find top-K attack paths through the technique graph.

        Args:
            techniques_tried: IDs of techniques that were attempted
            posteriors: Posterior state dict {tech_id: {alpha, beta, mean}}
            default_prob: Default success probability for untested techniques

        Returns:
            Top-K attack paths sorted by joint probability (descending)
        """
        # Build technique lookup
        tried_set = set(techniques_tried)
        techniques = {t.id: t for t in self.registry.get_all()}

        # Get probabilities from posteriors or defaults
        probs = self._get_probabilities(techniques_tried, posteriors, default_prob)

        # Build prerequisite graph from technique metadata
        graph = self._build_prerequisite_graph(techniques)

        # Beam search for paths
        paths = self._beam_search(techniques, graph, probs, tried_set)

        # Sort by joint probability and take top-K
        paths.sort(key=lambda p: p.joint_success_probability, reverse=True)
        return paths[:self.top_k]

    def _get_probabilities(
        self,
        techniques_tried: list[str],
        posteriors: dict | None,
        default_prob: float,
    ) -> dict[str, float]:
        """Get success probabilities from posteriors or defaults."""
        probs: dict[str, float] = {}
        for t in self.registry.get_all():
            if posteriors and t.id in posteriors:
                post = posteriors[t.id]
                if isinstance(post, dict):
                    probs[t.id] = post.get("mean", default_prob)
                else:
                    probs[t.id] = default_prob
            elif t.id in techniques_tried:
                probs[t.id] = default_prob
            else:
                probs[t.id] = default_prob
        return probs

    def _build_prerequisite_graph(
        self, techniques: dict[str, AttackTechnique]
    ) -> dict[str, list[str]]:
        """Build directed graph: technique → techniques it enables.

        Uses phase ordering + surface adjacency to infer relationships.
        """
        graph: dict[str, list[str]] = defaultdict(list)

        # Group techniques by phase
        by_phase: dict[Phase, list[AttackTechnique]] = defaultdict(list)
        for t in techniques.values():
            by_phase[t.phase].append(t)

        phase_list = sorted(KILL_CHAIN_ORDER.keys(), key=lambda p: KILL_CHAIN_ORDER[p])

        # Connect techniques: each phase enables the next
        for i, phase in enumerate(phase_list[:-1]):
            next_phase = phase_list[i + 1]
            for src in by_phase.get(phase, []):
                for tgt in by_phase.get(next_phase, []):
                    # Connect if they share a surface or have related goals
                    if src.surface == tgt.surface or self._goals_overlap(src, tgt):
                        graph[src.id].append(tgt.id)

        # Also connect via explicit prerequisites
        for t in techniques.values():
            for prereq in t.prerequisites:
                # Find techniques that satisfy this prerequisite tag
                for candidate in techniques.values():
                    if prereq in candidate.tags and candidate.id != t.id:
                        graph[candidate.id].append(t.id)

        return graph

    def _goals_overlap(self, t1: AttackTechnique, t2: AttackTechnique) -> bool:
        """Check if two techniques share any goals."""
        return bool(set(t1.goals_supported) & set(t2.goals_supported))

    def _beam_search(
        self,
        techniques: dict[str, AttackTechnique],
        graph: dict[str, list[str]],
        probs: dict[str, float],
        tried: set[str],
        beam_width: int = 20,
    ) -> list[AttackPath]:
        """Beam search for high-probability attack paths."""
        # Start from recon/probe techniques
        start_phases = {Phase.RECON, Phase.PROBE}
        starters = [t for t in techniques.values() if t.phase in start_phases]

        if not starters:
            starters = list(techniques.values())[:10]

        # Initialize beams
        beams: list[tuple[list[str], float]] = []
        for s in starters:
            prob = probs.get(s.id, 0.4)
            beams.append(([s.id], prob))

        completed: list[AttackPath] = []

        for _ in range(self.max_path_length - 1):
            next_beams: list[tuple[list[str], float]] = []

            for path, joint_prob in beams:
                last = path[-1]
                neighbors = graph.get(last, [])

                if not neighbors:
                    # Terminal path — create AttackPath
                    if len(path) >= 2:
                        completed.append(self._make_path(path, probs, techniques, joint_prob))
                    continue

                for neighbor in neighbors:
                    if neighbor in path:
                        continue  # No cycles
                    n_prob = probs.get(neighbor, 0.4)
                    # Adjust for correlation between same-surface techniques
                    adj_prob = self._adjust_for_correlation(
                        n_prob, path, neighbor, techniques
                    )
                    new_joint = joint_prob * adj_prob
                    next_beams.append((path + [neighbor], new_joint))

            # Keep top beam_width
            next_beams.sort(key=lambda x: x[1], reverse=True)
            beams = next_beams[:beam_width]

            # Also capture current length paths
            for path, joint_prob in beams:
                if len(path) >= 2:
                    completed.append(self._make_path(path, probs, techniques, joint_prob))

        return completed

    def _adjust_for_correlation(
        self,
        prob: float,
        path: list[str],
        new_id: str,
        techniques: dict[str, AttackTechnique],
    ) -> float:
        """Adjust probability for correlation with prior path techniques."""
        new_tech = techniques.get(new_id)
        if not new_tech:
            return prob

        # If same surface as previous technique, apply correlation discount
        for tid in path:
            t = techniques.get(tid)
            if t and t.surface == new_tech.surface:
                return prob * (1.0 - self.correlation_factor)

        return prob

    def _make_path(
        self,
        path: list[str],
        probs: dict[str, float],
        techniques: dict[str, AttackTechnique],
        joint_prob: float,
    ) -> AttackPath:
        """Create an AttackPath from a sequence of technique IDs."""
        names = [techniques[tid].name for tid in path if tid in techniques]
        individual = [probs.get(tid, 0.4) for tid in path]
        surfaces = [techniques[tid].surface.value for tid in path if tid in techniques]
        narrative = generate_narrative(path, individual, techniques)

        return AttackPath(
            technique_sequence=path,
            technique_names=names,
            individual_probabilities=individual,
            joint_success_probability=joint_prob,
            surfaces_traversed=surfaces,
            attack_narrative=narrative,
        )


def compute_joint_probability(
    chain: list[str],
    posteriors: dict[str, dict],
    correlation: float = 0.3,
) -> float:
    """Compute joint success probability for a technique chain.

    Adjusts for correlation between techniques on the same surface.
    """
    if not chain:
        return 0.0

    joint = 1.0
    seen_surfaces: set[str] = set()

    for tid in chain:
        post = posteriors.get(tid, {})
        prob = post.get("mean", 0.4) if isinstance(post, dict) else 0.4

        # Apply correlation discount for repeated surfaces
        surface = post.get("surface", "") if isinstance(post, dict) else ""
        if surface and surface in seen_surfaces:
            prob *= (1.0 - correlation)
        if surface:
            seen_surfaces.add(surface)

        joint *= prob

    return joint


def generate_narrative(
    chain: list[str],
    probabilities: list[float],
    techniques: dict[str, AttackTechnique],
) -> str:
    """Generate a human-readable attack narrative for a technique chain."""
    if not chain:
        return "Empty attack path."

    parts = []
    for i, tid in enumerate(chain):
        tech = techniques.get(tid)
        if not tech:
            continue

        prob = probabilities[i] if i < len(probabilities) else 0.0
        prob_pct = f"{prob*100:.0f}%"

        if i == 0:
            parts.append(
                f"Begin with {tech.name} ({tech.phase.value}) "
                f"on {tech.surface.value} surface [{prob_pct} success]"
            )
        elif i == len(chain) - 1:
            parts.append(
                f"Conclude with {tech.name} ({tech.phase.value}) "
                f"targeting {tech.surface.value} [{prob_pct} success]"
            )
        else:
            parts.append(
                f"Then apply {tech.name} ({tech.phase.value}) "
                f"on {tech.surface.value} [{prob_pct} success]"
            )

    return ". ".join(parts) + "."
