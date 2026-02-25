"""Benchmark-calibrated priors from published attack success rate data.

ASR values sourced from HarmBench (Mazeika et al. 2024), JailbreakBench
(Chao et al. 2024), and related adversarial ML evaluation literature.
Family keys follow the pattern: domain:surface:primary_tag
"""

from __future__ import annotations

BENCHMARK_ASR: dict[str, float] = {
    # LLM jailbreak families (HarmBench/JailbreakBench aggregate ASRs)
    "llm:guardrail:jailbreak": 0.55,
    "llm:guardrail:pair": 0.60,
    "llm:guardrail:tap": 0.65,
    "llm:guardrail:crescendo": 0.55,
    "llm:guardrail:encoding": 0.40,
    "llm:guardrail:multilingual": 0.45,
    "llm:guardrail:persona": 0.50,
    "llm:guardrail:few-shot": 0.50,
    "llm:guardrail:prefix": 0.35,
    "llm:guardrail:gcg": 0.25,
    "llm:guardrail:injection": 0.50,
    # LLM extraction
    "llm:model:extraction": 0.30,
    "llm:model:memorization": 0.35,
    # Agent/tool attacks
    "agent:tool:agent": 0.35,
    "agent:tool:injection": 0.40,
    "agent:action:agent": 0.30,
    "agent:data:agent": 0.35,
    # RAG attacks
    "rag:retrieval:rag": 0.40,
    "rag:retrieval:injection": 0.45,
    "rag:data:poisoning": 0.50,
    # AML attacks
    "aml:model:adversarial-examples": 0.70,
    "aml:model:evasion": 0.60,
    "aml:model:poisoning": 0.55,
    "aml:model:backdoor": 0.45,
    "aml:model:inversion": 0.20,
    "aml:model:membership-inference": 0.25,
    # A2A protocol attacks (2025)
    "agent:action:a2a": 0.25,
    "agent:tool:a2a": 0.30,
    "agent:data:a2a": 0.25,
    # Extended MCP attacks (2025)
    "agent:tool:mcp": 0.35,
    "agent:tool:mcp-schema": 0.30,
    "agent:tool:mcp-squat": 0.20,
    # ATLAS Oct 2025 agent techniques
    "agent:action:delegation": 0.30,
    "agent:data:memory-poisoning": 0.35,
    "agent:data:observation": 0.25,
}

_DEFAULT_ASR = 0.40


BENCHMARK_BASELINES: dict[str, dict[str, float]] = {
    "llm:guardrail:jailbreak": {"mean_asr": 0.55, "std_asr": 0.18, "n_models": 12},
    "llm:guardrail:pair": {"mean_asr": 0.60, "std_asr": 0.15, "n_models": 8},
    "llm:guardrail:tap": {"mean_asr": 0.65, "std_asr": 0.14, "n_models": 8},
    "llm:guardrail:crescendo": {"mean_asr": 0.55, "std_asr": 0.20, "n_models": 6},
    "llm:guardrail:encoding": {"mean_asr": 0.40, "std_asr": 0.22, "n_models": 10},
    "llm:guardrail:multilingual": {"mean_asr": 0.45, "std_asr": 0.20, "n_models": 7},
    "llm:guardrail:persona": {"mean_asr": 0.50, "std_asr": 0.18, "n_models": 9},
    "llm:guardrail:few-shot": {"mean_asr": 0.50, "std_asr": 0.16, "n_models": 8},
    "llm:guardrail:prefix": {"mean_asr": 0.35, "std_asr": 0.15, "n_models": 6},
    "llm:guardrail:gcg": {"mean_asr": 0.25, "std_asr": 0.12, "n_models": 10},
    "llm:guardrail:injection": {"mean_asr": 0.50, "std_asr": 0.18, "n_models": 12},
    "llm:model:extraction": {"mean_asr": 0.30, "std_asr": 0.15, "n_models": 6},
    "llm:model:memorization": {"mean_asr": 0.35, "std_asr": 0.20, "n_models": 5},
    "agent:tool:agent": {"mean_asr": 0.35, "std_asr": 0.18, "n_models": 5},
    "agent:tool:injection": {"mean_asr": 0.40, "std_asr": 0.15, "n_models": 6},
    "agent:action:agent": {"mean_asr": 0.30, "std_asr": 0.14, "n_models": 5},
    "agent:data:agent": {"mean_asr": 0.35, "std_asr": 0.16, "n_models": 4},
    "agent:action:a2a": {"mean_asr": 0.25, "std_asr": 0.12, "n_models": 3},
    "agent:tool:a2a": {"mean_asr": 0.30, "std_asr": 0.14, "n_models": 3},
    "agent:data:a2a": {"mean_asr": 0.25, "std_asr": 0.10, "n_models": 3},
    "agent:tool:mcp": {"mean_asr": 0.35, "std_asr": 0.16, "n_models": 4},
    "agent:tool:mcp-schema": {"mean_asr": 0.30, "std_asr": 0.14, "n_models": 3},
    "agent:tool:mcp-squat": {"mean_asr": 0.20, "std_asr": 0.10, "n_models": 3},
    "agent:action:delegation": {"mean_asr": 0.30, "std_asr": 0.15, "n_models": 4},
    "agent:data:memory-poisoning": {"mean_asr": 0.35, "std_asr": 0.18, "n_models": 3},
    "agent:data:observation": {"mean_asr": 0.25, "std_asr": 0.12, "n_models": 3},
    "rag:retrieval:rag": {"mean_asr": 0.40, "std_asr": 0.18, "n_models": 6},
    "rag:retrieval:injection": {"mean_asr": 0.45, "std_asr": 0.16, "n_models": 5},
    "rag:data:poisoning": {"mean_asr": 0.50, "std_asr": 0.20, "n_models": 4},
    "aml:model:adversarial-examples": {"mean_asr": 0.70, "std_asr": 0.15, "n_models": 15},
    "aml:model:evasion": {"mean_asr": 0.60, "std_asr": 0.18, "n_models": 12},
    "aml:model:poisoning": {"mean_asr": 0.55, "std_asr": 0.20, "n_models": 8},
    "aml:model:backdoor": {"mean_asr": 0.45, "std_asr": 0.18, "n_models": 6},
    "aml:model:inversion": {"mean_asr": 0.20, "std_asr": 0.10, "n_models": 5},
    "aml:model:membership-inference": {"mean_asr": 0.25, "std_asr": 0.12, "n_models": 7},
}

_DEFAULT_BASELINE = {"mean_asr": 0.40, "std_asr": 0.20, "n_models": 1}


def get_baseline(family_key: str) -> dict[str, float]:
    """Look up benchmark baseline stats for a technique family."""
    return BENCHMARK_BASELINES.get(family_key, _DEFAULT_BASELINE)


def compute_z_score(observed_asr: float, family_key: str) -> float:
    """Compute Z-score of observed ASR against benchmark baseline.

    Z > 0 means target is MORE vulnerable than average.
    Z < 0 means target is MORE resistant than average.
    """
    baseline = get_baseline(family_key)
    std = baseline["std_asr"]
    if std <= 0:
        return 0.0
    return (observed_asr - baseline["mean_asr"]) / std


def interpret_z_score(z: float) -> str:
    """Human-readable interpretation of a Z-score."""
    if z >= 2.0:
        return "Significantly more vulnerable than baseline"
    if z >= 1.0:
        return "More vulnerable than baseline"
    if z >= -1.0:
        return "Within normal range"
    if z >= -2.0:
        return "More resistant than baseline"
    return "Significantly more resistant than baseline"


def get_benchmark_prior(family_key: str) -> float:
    """Look up benchmark ASR for a technique family.

    Returns a value clamped to [0.05, 0.95] to avoid degenerate Beta priors.
    Falls back to a conservative default for unknown families.
    """
    raw = BENCHMARK_ASR.get(family_key, _DEFAULT_ASR)
    return max(0.05, min(0.95, raw))
