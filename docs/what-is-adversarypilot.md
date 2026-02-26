---
layout: page
title: "What is AdversaryPilot? Bayesian AI Red Teaming Explained"
description: "AdversaryPilot is an open-source Bayesian attack planner for AI red teaming. Uses Thompson Sampling to prioritize 70 ATLAS-aligned attack techniques."
permalink: /what-is-adversarypilot/
---

# What is AdversaryPilot?

AdversaryPilot is an open-source **Bayesian attack planning engine** for adversarial testing of LLM, agent, and ML systems. It uses [Thompson Sampling](https://en.wikipedia.org/wiki/Thompson_sampling) to decide which attack techniques to try next, learns from every test result, and generates compliance-ready reports.

It is **not** another attack execution tool. Instead, it sits above tools like [garak](https://github.com/NVIDIA/garak), [promptfoo](https://github.com/promptfoo/promptfoo), and [PyRIT](https://github.com/Azure/PyRIT) as the strategic planning layer.

## The Problem: Red Teaming Without Strategy

Most AI red team engagements today follow an ad hoc pattern:

1. Pick a few jailbreak prompts from a blog post or benchmark
2. Run them against the target
3. Record pass/fail results
4. Write a report

This approach misses critical questions:

- **Coverage**: Which attack surfaces were never tested? Which compliance controls have gaps?
- **Prioritization**: Of the 70+ known attack techniques, which ones are most likely to succeed against *this specific target*?
- **Statistical rigor**: Is a 40% attack success rate on DAN prompts meaningful, or is that the expected baseline?
- **Sequencing**: Should you extract the system prompt first to inform later jailbreak attempts?

AdversaryPilot answers all of these.

## The Solution: Bayesian Attack Planning

At its core, AdversaryPilot maintains a **Beta distribution posterior** for each of its 70 attack techniques. This posterior represents the engine's current belief about how likely each technique is to succeed against the target.

### How Thompson Sampling Drives Decisions

1. **Prior initialization**: Each technique starts with a Beta(alpha, beta) prior calibrated from published benchmark data (HarmBench, JailbreakBench). A technique known to have ~45% ASR across benchmarks gets an informative prior, not a flat one.

2. **Sampling**: When asked "what should I try next?", the planner samples from each technique's posterior. This naturally balances **exploration** (trying uncertain techniques) with **exploitation** (repeating techniques that have worked).

3. **Updating**: After you run a technique and import results, the posterior updates. Success increments alpha; failure increments beta. Correlated arms ensure that success on one jailbreak technique boosts related techniques in the same family.

4. **Two-phase campaigns**: The planner operates in two phases - **probe** (broad exploration across surfaces) and **exploit** (deep testing of discovered weaknesses). Thompson Sampling naturally transitions between these.

## 70 Techniques Across 3 Domains

Every technique is mapped to the [MITRE ATLAS](https://atlas.mitre.org/) framework with full metadata including access requirements, stealth profiles, execution cost, and compliance references.

| Domain | Count | Examples |
|--------|-------|---------|
| **LLM** | 33 | DAN Jailbreak, PAIR, TAP, GCG, Crescendo, Skeleton Key, prompt injection, system prompt extraction, encoding bypass, RAG poisoning |
| **Agent** | 25 | Goal hijacking, MCP tool poisoning, A2A impersonation, delegation abuse, memory poisoning, chain escape |
| **AML** | 12 | FGSM, PGD, transfer attacks, backdoor poisoning, model extraction, embedding inversion |

See the [full MITRE ATLAS technique catalog]({{ '/mitre-atlas-ai-red-teaming-planner/' | relative_url }}) for details.

## What Makes It Different?

|  | AdversaryPilot | garak | PyRIT | promptfoo | HarmBench |
|--|---|---|---|---|---|
| **Focus** | Attack *strategy* | Attack *execution* | Attack *execution* | Eval & red team | Benchmark |
| **Planning** | Bayesian Thompson Sampling | None | Orchestrator scoring | None | None |
| **Adaptive** | Yes (posterior updates) | No | Limited | No | No |
| **Techniques** | 70 (LLM + Agent + AML) | 100+ probes | 20+ strategies | 15+ tests | 18 methods |
| **Compliance** | OWASP + NIST + EU AI Act | None | None | OWASP partial | None |
| **Z-Score Calibration** | Yes (vs benchmarks) | Z-score (reference models) | No | No | Provides baselines |
| **Attack Paths** | Yes (joint probabilities) | No | Multi-turn chains | No | No |
| **Meta-Learning** | Yes (cross-campaign) | No | No | No | No |

AdversaryPilot does not compete with these tools - it **orchestrates** them. Import results from [garak]({{ '/garak-results-analysis/' | relative_url }}) or [promptfoo]({{ '/promptfoo-attack-planning/' | relative_url }}), get the next recommended technique with a rationale, and generate reports that map to compliance frameworks.

## Architecture Overview

```
adversarypilot/
├── models/          Pydantic domain models (Target, Technique, Campaign, Report)
├── taxonomy/        70-technique ATLAS-aligned catalog with compliance refs
├── prioritizer/     7-dimension weighted scoring + sensitivity analysis
├── planner/         Thompson Sampling, attack paths, meta-learning, priors
├── campaign/        Campaign lifecycle: create -> recommend -> update -> report
├── reporting/       HTML reports, compliance analysis, Z-score calibration
├── importers/       garak + promptfoo result importers
├── hooks/           Execution command generation for external tools
├── replay/          Decision replay and verification
├── utils/           Hashing, logging, timestamps
└── cli/             Typer CLI interface
```

The planner pipeline:

1. **Hard filters** remove techniques incompatible with the target (wrong access level, wrong domain, unsupported target type)
2. **7-dimension scorer** evaluates compatibility, access fit, goal alignment, defense bypass likelihood, signal gain, cost, and detection risk
3. **Thompson Sampling** overlays Bayesian posteriors to produce the final ranked recommendation

<img src="{{ '/screenshots/layer-analysis.png' | relative_url }}" alt="Attack surface layer analysis with Wilson confidence intervals and Z-score badges">

## Getting Started

```bash
pip install -e ".[dev]"
adversarypilot plan target.yaml
```

Read the [AI Red Team Strategy guide]({{ '/ai-red-team-strategy/' | relative_url }}) to learn how to build a systematic red team campaign, or explore [attack sequencing]({{ '/adversarial-attack-sequencing/' | relative_url }}) to understand multi-stage attack planning.

<img src="{{ '/screenshots/raw-data.png' | relative_url }}" alt="Raw data JSON export for programmatic analysis">

## Related Pages

- [AI Red Team Strategy]({{ '/ai-red-team-strategy/' | relative_url }}) - Building a systematic red team methodology
- [MITRE ATLAS Red Teaming Planner]({{ '/mitre-atlas-ai-red-teaming-planner/' | relative_url }}) - Full technique catalog
- [Analyzing Garak Results]({{ '/garak-results-analysis/' | relative_url }}) - Import and analyze garak output
- [Promptfoo Attack Planning]({{ '/promptfoo-attack-planning/' | relative_url }}) - Plan and analyze promptfoo tests
