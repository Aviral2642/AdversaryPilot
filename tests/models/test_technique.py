"""Tests for technique models."""

from adversarypilot.models.technique import AttackTechnique, AtlasReference, TechniqueExecutionSpec


def test_attack_technique_creation(sample_technique):
    assert sample_technique.id == "AP-TX-TEST-001"
    assert sample_technique.domain == "llm"
    assert sample_technique.base_cost == 0.3
    assert len(sample_technique.atlas_refs) == 1
    assert sample_technique.atlas_refs[0].atlas_id == "AML.T0051"


def test_technique_serialization_roundtrip(sample_technique):
    json_str = sample_technique.model_dump_json()
    restored = AttackTechnique.model_validate_json(json_str)
    assert restored.id == sample_technique.id
    assert restored.atlas_refs[0].atlas_id == sample_technique.atlas_refs[0].atlas_id


def test_atlas_reference():
    ref = AtlasReference(atlas_id="AML.T0020", atlas_name="Poison Training Data", tactic="ML Attack Staging")
    assert ref.atlas_id == "AML.T0020"


def test_technique_execution_spec():
    spec = TechniqueExecutionSpec(
        technique_id="AP-TX-TEST-001",
        query_budget=50,
        seed=42,
        timeout_seconds=300,
    )
    assert spec.technique_id == "AP-TX-TEST-001"
    assert spec.query_budget == 50
    assert spec.seed == 42


def test_technique_cost_bounds():
    t = AttackTechnique(
        id="test", name="test", domain="llm", phase="exploit",
        surface="model", access_required="black_box", base_cost=0.0,
    )
    assert t.base_cost == 0.0

    t2 = AttackTechnique(
        id="test2", name="test2", domain="llm", phase="exploit",
        surface="model", access_required="black_box", base_cost=1.0,
    )
    assert t2.base_cost == 1.0
