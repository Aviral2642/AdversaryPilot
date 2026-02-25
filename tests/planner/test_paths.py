"""Tests for attack path analysis (WS5)."""

import pytest

from adversarypilot.planner.paths import (
    AttackPath,
    AttackPathAnalyzer,
    compute_joint_probability,
    generate_narrative,
)
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


@pytest.fixture
def analyzer(registry):
    return AttackPathAnalyzer(registry=registry, top_k=5)


class TestAttackPath:
    def test_model_creation(self):
        path = AttackPath(
            technique_sequence=["T1", "T2"],
            technique_names=["Technique 1", "Technique 2"],
            individual_probabilities=[0.5, 0.6],
            joint_success_probability=0.3,
            surfaces_traversed=["model", "data"],
            attack_narrative="Test narrative.",
        )
        assert path.joint_success_probability == 0.3
        assert len(path.technique_sequence) == 2

    def test_to_dict(self):
        path = AttackPath(
            technique_sequence=["T1"],
            individual_probabilities=[0.5],
            joint_success_probability=0.5,
        )
        d = path.to_dict()
        assert "technique_sequence" in d
        assert "joint_success_probability" in d


class TestAttackPathAnalyzer:
    def test_analyze_returns_paths(self, analyzer):
        paths = analyzer.analyze(techniques_tried=[])
        assert isinstance(paths, list)

    def test_analyze_with_tried_techniques(self, analyzer):
        tried = ["AP-TX-LLM-JAILBREAK-DAN", "AP-TX-LLM-INJECT-DIRECT"]
        paths = analyzer.analyze(techniques_tried=tried)
        assert len(paths) > 0

    def test_paths_have_sequences(self, analyzer):
        paths = analyzer.analyze(techniques_tried=[])
        for path in paths:
            assert len(path.technique_sequence) >= 2

    def test_paths_have_probabilities(self, analyzer):
        paths = analyzer.analyze(techniques_tried=[])
        for path in paths:
            assert 0.0 <= path.joint_success_probability <= 1.0
            assert len(path.individual_probabilities) == len(path.technique_sequence)

    def test_paths_sorted_by_probability(self, analyzer):
        paths = analyzer.analyze(techniques_tried=[])
        if len(paths) >= 2:
            for i in range(len(paths) - 1):
                assert paths[i].joint_success_probability >= paths[i + 1].joint_success_probability

    def test_paths_have_narratives(self, analyzer):
        paths = analyzer.analyze(techniques_tried=[])
        for path in paths:
            assert len(path.attack_narrative) > 0

    def test_paths_have_surfaces(self, analyzer):
        paths = analyzer.analyze(techniques_tried=[])
        for path in paths:
            assert len(path.surfaces_traversed) > 0

    def test_top_k_limit(self, registry):
        analyzer = AttackPathAnalyzer(registry=registry, top_k=3)
        paths = analyzer.analyze(techniques_tried=[])
        assert len(paths) <= 3

    def test_with_posteriors(self, analyzer):
        posteriors = {
            "AP-TX-LLM-JAILBREAK-DAN": {"alpha": 5, "beta": 3, "mean": 0.625},
            "AP-TX-LLM-INJECT-DIRECT": {"alpha": 3, "beta": 5, "mean": 0.375},
        }
        paths = analyzer.analyze(
            techniques_tried=["AP-TX-LLM-JAILBREAK-DAN"],
            posteriors=posteriors,
        )
        assert len(paths) > 0


class TestComputeJointProbability:
    def test_empty_chain(self):
        assert compute_joint_probability([], {}) == 0.0

    def test_single_technique(self):
        posteriors = {"T1": {"mean": 0.5, "surface": "model"}}
        p = compute_joint_probability(["T1"], posteriors)
        assert abs(p - 0.5) < 0.001

    def test_two_independent(self):
        posteriors = {
            "T1": {"mean": 0.5, "surface": "model"},
            "T2": {"mean": 0.6, "surface": "data"},
        }
        p = compute_joint_probability(["T1", "T2"], posteriors)
        assert abs(p - 0.3) < 0.001

    def test_correlation_reduces_probability(self):
        posteriors = {
            "T1": {"mean": 0.5, "surface": "model"},
            "T2": {"mean": 0.5, "surface": "model"},  # Same surface
        }
        p = compute_joint_probability(["T1", "T2"], posteriors, correlation=0.3)
        # T2 gets discounted: 0.5 * (0.5 * 0.7) = 0.175
        assert p < 0.25  # Less than independent

    def test_unknown_posteriors(self):
        p = compute_joint_probability(["T1", "T2"], {})
        # Both use default 0.4
        assert abs(p - 0.16) < 0.01


class TestGenerateNarrative:
    def test_empty_chain(self):
        result = generate_narrative([], [], {})
        assert "Empty" in result

    def test_single_technique(self, registry):
        techniques = {t.id: t for t in registry.get_all()}
        tid = "AP-TX-LLM-JAILBREAK-DAN"
        result = generate_narrative([tid], [0.5], techniques)
        assert "Begin with" in result
        assert "DAN" in result

    def test_multi_step(self, registry):
        techniques = {t.id: t for t in registry.get_all()}
        tids = ["AP-TX-LLM-JAILBREAK-DAN", "AP-TX-LLM-INJECT-DIRECT"]
        result = generate_narrative(tids, [0.5, 0.6], techniques)
        assert "Begin with" in result
        assert "Conclude with" in result
