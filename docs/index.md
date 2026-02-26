---
layout: page
title: "AdversaryPilot - Bayesian Attack Planning for LLM & AI Security Testing"
description: "Open-source Bayesian attack planning engine with 70 MITRE ATLAS techniques for LLM, agent, and ML red teaming. Imports garak & promptfoo results."
permalink: /
---

# AdversaryPilot: The AI Red Team Strategist

**Bayesian attack planning and orchestration for LLM, agent, and ML systems.**

AdversaryPilot is the **strategic brain** that sits above your attack tools. It decides *what to try next* and *why*, while tools like [garak](https://github.com/NVIDIA/garak), [promptfoo](https://github.com/promptfoo/promptfoo), and [PyRIT](https://github.com/Azure/PyRIT) handle execution.

Existing red teaming tools are excellent at *running* attacks. But they don't answer the harder questions:

- **"What should I try next?"** — Thompson Sampling explores the most promising techniques while balancing exploitation and exploration.
- **"Which layer is weakest?"** — Bayesian posterior analysis identifies the most vulnerable system layer with calibrated confidence intervals.
- **"Are these results meaningful?"** — Z-score calibration against HarmBench and JailbreakBench tells you if a 40% attack success rate is alarming or expected.
- **"Am I meeting compliance?"** — Automated mapping to OWASP LLM Top 10, NIST AI RMF, and EU AI Act shows which controls you've tested and which gaps remain.

![AdversaryPilot executive summary showing risk level, technique coverage, and compliance gauges](screenshots/executive-summary.png)

## Key Capabilities

**Bayesian Attack Planning** — Thompson Sampling with correlated arms and benchmark-calibrated priors. The planner learns from every test result and recommends increasingly targeted techniques.

**70 MITRE ATLAS Techniques** — Covering LLM jailbreaks (DAN, PAIR, TAP, GCG, Crescendo), prompt injection, agent exploitation (MCP poisoning, A2A impersonation), and classical AML attacks (FGSM, PGD, model extraction).

**Compliance Mapping** — Every technique maps to OWASP LLM Top 10, NIST AI RMF, and EU AI Act. Reports show per-framework coverage and identify untested controls.

**Z-Score Calibration** — Results are calibrated against published benchmarks from HarmBench and JailbreakBench, reported as standard deviations from baseline.

**Tool Integrations** — Import results from [garak](https://github.com/NVIDIA/garak) (27 probe mappings) and [promptfoo](https://github.com/promptfoo/promptfoo) (11 test mappings). Execution hooks generate ready-to-run shell commands.

**Self-Contained HTML Reports** — 10 interactive tabs including attack graphs, compliance dashboards, belief evolution, and risk heatmaps. Zero dependencies — open in any browser.

## How the Planner Works

```
Target Profile
     |
     v
+--------------+     +---------------+     +------------------+
| Hard Filters | --> | 7-Dim Scorer  | --> | Thompson Sample  |
| (access,     |     | (compat, fit, |     | (Beta posterior,  |
|  domain,     |     |  defense,     |     |  correlated arms, |
|  target)     |     |  signal,      |     |  priors from      |
|              |     |  cost, risk)  |     |  benchmarks)      |
+--------------+     +---------------+     +------------------+
                                                   |
                                                   v
                                          +------------------+
                                          | Ranked Plan with |
                                          | rationale, hooks,|
                                          | confidence, and  |
                                          | Z-scores         |
                                          +------------------+
```

## Quick Start

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+. Only 4 dependencies: `pydantic`, `typer`, `rich`, `pyyaml`.

```bash
# Generate a ranked attack plan
adversarypilot plan target.yaml

# Run an adaptive campaign
adversarypilot campaign new target.yaml --name "pentest-q1"

# Import results from your tools
adversarypilot import garak garak_report.jsonl

# Get Bayesian-updated recommendations
adversarypilot campaign next <campaign-id>

# Generate the defender report
adversarypilot report <campaign-id>
```

## Explore the Documentation

| Guide | What You'll Learn |
|-------|-------------------|
| [What is AdversaryPilot?]({{ '/what-is-adversarypilot/' | relative_url }}) | How Bayesian attack planning works and how it compares to existing tools |
| [AI Red Team Strategy]({{ '/ai-red-team-strategy/' | relative_url }}) | Building a systematic, compliance-driven AI red team methodology |
| [MITRE ATLAS Red Teaming Planner]({{ '/mitre-atlas-ai-red-teaming-planner/' | relative_url }}) | Full catalog of 70 ATLAS-aligned techniques with compliance cross-mapping |
| [Adversarial Attack Sequencing]({{ '/adversarial-attack-sequencing/' | relative_url }}) | Multi-stage attack paths with joint success probabilities |
| [Analyzing Garak Results]({{ '/garak-results-analysis/' | relative_url }}) | Import garak output for Bayesian analysis and compliance reporting |
| [Promptfoo Attack Planning]({{ '/promptfoo-attack-planning/' | relative_url }}) | Plan and analyze promptfoo red team tests |

![Force-directed attack graph visualization showing technique relationships](screenshots/attack-graph.png)
