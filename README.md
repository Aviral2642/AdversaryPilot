<div align="center">

# AdversaryPilot

### The AI Red Team Strategist

**Bayesian attack planning and orchestration for LLM, agent, and ML systems.**

Think of it as the **strategic brain** that sits above your attack tools — it decides *what* to try next and *why*, while [garak](https://github.com/NVIDIA/garak), [promptfoo](https://github.com/promptfoo/promptfoo), and [PyRIT](https://github.com/Azure/PyRIT) do the execution.

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-626%20passed-brightgreen.svg)]()
[![Techniques](https://img.shields.io/badge/techniques-70-orange.svg)]()
[![MITRE ATLAS](https://img.shields.io/badge/MITRE%20ATLAS-aligned-red.svg)](https://atlas.mitre.org/)

[Quick Start](#quick-start) · [Features](#key-features) · [CLI Reference](#cli-reference) · [Architecture](#architecture) · [Techniques](#technique-catalog) · [Compliance](#compliance--reporting) · [Citations](#citations--references)

</div>

---

## What is AdversaryPilot?

AdversaryPilot is an **ATLAS-aligned attack planning engine** that brings strategic intelligence to adversarial ML testing. While existing tools excel at *running* attacks, they don't answer the harder questions:

- **"What should I try next?"** — Thompson Sampling with correlated arms explores the most promising attack surfaces while balancing exploitation and exploration.
- **"Which layer is weakest?"** — Bayesian posterior analysis identifies the most vulnerable system layer with calibrated confidence intervals.
- **"Are these results meaningful?"** — Z-score calibration against benchmark baselines (HarmBench, JailbreakBench) tells you if a 40% ASR is alarming or expected.
- **"Am I meeting compliance?"** — Automated mapping to OWASP LLM Top 10, NIST AI RMF, and EU AI Act shows exactly which controls you've tested and which gaps remain.

AdversaryPilot doesn't replace your attack tools — it **orchestrates** them. Import results from garak or promptfoo, get the next recommended technique with a rationale, and generate self-contained HTML reports that a CISO can actually read.

---

## Key Features

**Bayesian Attack Planning**
Thompson Sampling with correlated arms and benchmark-calibrated priors. The planner learns from every test result, updating Beta distribution posteriors to recommend increasingly targeted techniques. Two-phase campaigns (probe → exploit) mirror real-world red team methodology.

**70 Attack Techniques Across 4 Surfaces**
Comprehensive catalog covering LLM jailbreaks (DAN, PAIR, TAP, GCG, Crescendo, Skeleton Key), prompt injection, data extraction, agent exploitation (MCP tool poisoning, A2A impersonation, delegation abuse), and classical AML attacks (FGSM, PGD, poisoning, model extraction). Every technique maps to MITRE ATLAS with full metadata.

**Compliance Framework Mapping**
Every technique links to OWASP LLM Top 10 (LLM01–LLM10), NIST AI RMF (GOVERN, MAP, MEASURE, MANAGE), and EU AI Act articles. Reports show per-framework coverage gauges and identify untested controls — critical for procurement and audit readiness.

**Z-Score Calibration**
Raw attack success rates are uninterpretable without context. AdversaryPilot calibrates every result against published benchmarks from HarmBench and JailbreakBench, reporting findings as "X sigma from baseline" with statistical significance indicators.

**Self-Contained HTML Reports**
Zero-dependency, dark-themed HTML reports with 10 interactive tabs: Executive Summary, Attack Graph (force-directed Canvas visualization), Layer Analysis with confidence intervals, Risk Heatmap, Technique Details, ATLAS Mapping, Compliance Dashboard, Belief Evolution, Statistics, and Raw Data export.

**Attack Path Analysis**
Beam search over technique dependency graphs with joint success probabilities. Generates human-readable attack narratives: "Extract system prompt (72%) → Identify filtering gaps (58%) → Chain prompt injection (34%) — Joint P(success): 14.2%"

**Sensitivity Analysis**
Perturbs each scoring weight ±20% and measures Kendall tau rank correlation to show which parameters most influence technique rankings. Ensures recommendations aren't artifacts of arbitrary weight choices.

**Tool Integrations**
Import results from [garak](https://github.com/NVIDIA/garak) (27 probe mappings) and [promptfoo](https://github.com/promptfoo/promptfoo) (11 test mappings). Execution hooks generate the exact shell commands to run recommended techniques in external tools.

**Meta-Learning Across Campaigns**
Posterior cache stores learned attack probabilities by target profile. New campaigns against similar targets warm-start from nearest-neighbor posteriors using weighted Jaccard distance over target attributes.

**Trust & Reproducibility Package**
Every report includes an audit trail (operator, tool version, config hashes), reproducibility token (SHA-256 of all inputs), and assessment quality score measuring evidence depth, coverage breadth, and statistical power.

---

## Quick Start

### Install

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+. Only 4 dependencies: `pydantic`, `typer`, `rich`, `pyyaml`.

### 1. Define a Target

```yaml
# target.yaml
schema_version: "1.0"
name: Production Chatbot
target_type: chatbot
access_level: black_box
constraints:
  max_queries: 500
  stealth_priority: moderate
defenses:
  has_moderation: true
  has_input_filtering: true
goals:
  - jailbreak
  - extraction
```

### 2. Generate an Attack Plan

```bash
adversarypilot plan target.yaml
```

```
Attack Plan for: Production Chatbot
Target: chatbot (black_box)
Techniques: 12

  #1  System Prompt Extraction (AP-TX-LLM-EXTRACT-SYSPROMPT)
      Score: 3.14  |  Prior ASR: 0.55 ± 0.20
      strong fit for chatbot targets; low cost; high signal value
      Run: garak --model_type openai --probes probes.leakreplay.LiteraryRecitation

  #2  Crescendo Multi-Turn Jailbreak (AP-TX-LLM-CRESCENDO)
      Score: 2.98  |  Prior ASR: 0.45 ± 0.25
      effective against moderation; moderate stealth profile
      Run: garak --model_type openai --probes probes.crescendo.Crescendo
  ...
```

### 3. Run a Campaign

```bash
# Create an adaptive campaign
adversarypilot campaign new target.yaml --name "pentest-q1-2026"

# Import results from your attack tools
adversarypilot import garak garak_report.jsonl

# Get next recommendations (Bayesian-updated)
adversarypilot campaign next <campaign-id>

# Generate the defender report
adversarypilot report <campaign-id>
```

### 4. Open the HTML Report

The report command generates a self-contained HTML file with interactive visualizations — no server required. Open it in any browser.

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `adversarypilot plan <target.yaml>` | Generate ranked attack plan with execution hooks |
| `adversarypilot validate <target.yaml>` | Validate target profile schema |
| `adversarypilot techniques list` | List all techniques (filter: `--domain`, `--surface`, `--goal`, `--tool`) |
| `adversarypilot campaign new <target.yaml>` | Create adaptive campaign with Thompson Sampling |
| `adversarypilot campaign next <id>` | Get Bayesian-updated next recommendations |
| `adversarypilot report <id>` | Generate HTML defender report with compliance analysis |
| `adversarypilot import garak <file>` | Import garak JSONL results |
| `adversarypilot import promptfoo <file>` | Import promptfoo JSON results |
| `adversarypilot chains <target.yaml>` | Generate multi-stage attack chains |
| `adversarypilot replay <id>` | Replay campaign planning decisions |
| `adversarypilot version` | Show version |

---

## Library API

```python
from adversarypilot.models.target import TargetProfile
from adversarypilot.taxonomy.registry import TechniqueRegistry
from adversarypilot.prioritizer.engine import PrioritizerEngine
from adversarypilot.campaign.manager import CampaignManager
from adversarypilot.reporting.compliance import ComplianceAnalyzer

# Load target
target = TargetProfile(
    name="My RAG System",
    target_type="rag",
    access_level="black_box",
    goals=["extraction", "poisoning"],
    defenses={"has_moderation": True, "has_retrieval_filtering": False},
)

# Generate prioritized plan
registry = TechniqueRegistry()
registry.load_catalog()
engine = PrioritizerEngine()
plan = engine.plan(target, registry)

for entry in plan.entries[:5]:
    print(f"#{entry.rank} {entry.technique_name} (score={entry.score.total:.2f})")
    print(f"  {entry.rationale}")
    for hook in entry.execution_hooks:
        print(f"  $ {hook}")

# Run adaptive campaign
manager = CampaignManager()
campaign = manager.create(target, registry)

# After importing results...
next_techniques = manager.recommend_next(campaign)

# Analyze compliance coverage
analyzer = ComplianceAnalyzer()
summaries = analyzer.analyze(
    techniques_tried=campaign.state.techniques_tried,
    evaluations=campaign.state.evaluations,
)
for s in summaries:
    print(f"{s.framework}: {s.coverage_pct:.0%} controls tested")
```

---

## Architecture

```
adversarypilot/
├── models/          Pydantic domain models (Target, Technique, Campaign, Report)
├── taxonomy/        70-technique ATLAS-aligned catalog with compliance refs
├── prioritizer/     7-dimension weighted scoring + sensitivity analysis
├── planner/         Thompson Sampling, attack paths, meta-learning, priors
├── campaign/        Campaign lifecycle: create → recommend → update → report
├── reporting/       HTML reports, compliance analysis, Z-score calibration
├── importers/       garak + promptfoo result importers
├── hooks/           Execution command generation for external tools
├── replay/          Decision replay and verification
├── utils/           Hashing, logging, timestamps
└── cli/             Typer CLI interface
```

### How the Planner Works

```
Target Profile
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Hard Filters │ ──▶ │ 7-Dim Scorer │ ──▶ │ Thompson Sample │
│ (access,     │     │ (compat, fit,│     │ (Beta posterior, │
│  domain,     │     │  defense,    │     │  correlated     │
│  target)     │     │  signal,     │     │  arms, priors   │
│              │     │  cost, risk) │     │  from baselines)│
└─────────────┘     └──────────────┘     └─────────────────┘
                                                  │
                                                  ▼
                                         ┌─────────────────┐
                                         │ Ranked Plan with │
                                         │ rationale, hooks,│
                                         │ confidence, Z-   │
                                         │ scores, paths    │
                                         └─────────────────┘
```

**Scoring Dimensions**: compatibility (target type match), access fit, goal alignment, defense bypass likelihood, signal gain (information value), cost penalty, detection risk penalty — each configurable in `config.yaml`.

**Thompson Sampling**: Each technique maintains a Beta(α, β) posterior. Priors are calibrated from HarmBench/JailbreakBench published ASR data across 25+ attack families. Correlated arms ensure that success on one jailbreak technique boosts related techniques.

---

## Technique Catalog

70 techniques across 3 domains, mapped to [MITRE ATLAS](https://atlas.mitre.org/):

| Domain | Count | Key Techniques |
|--------|-------|---------------|
| **LLM** | 33 | DAN Jailbreak, PAIR Iterative, TAP Tree-of-Attacks, GCG Adversarial Suffix, AutoDAN Genetic, Crescendo Multi-Turn, Skeleton Key, Prompt Injection (direct/indirect), System Prompt Extraction, Encoding Bypass, Cross-Lingual Bypass, Context Window Overflow, Fine-Tuning Safety Removal, Poisoned RAG Retrieval |
| **Agent** | 25 | Goal Hijacking, Tool Misuse Induction, MCP Tool Poisoning, MCP Schema Injection, MCP Server Squatting, A2A Agent Impersonation, A2A Task Poisoning, Delegation Abuse, Memory Poisoning, Observation Manipulation, Chain Escape, Data Exfiltration, Privilege Escalation |
| **AML** | 12 | FGSM/PGD Evasion, Transfer Attacks, Backdoor Poisoning, Clean-Label Poisoning, Model Extraction, Embedding Inversion, Supply Chain Attacks |

Each technique includes: ATLAS cross-references, compliance mappings, execution cost, stealth profile, access requirements, goal tags, tool support flags, and benchmark ASR priors.

### 2025 Attack Surfaces

Includes coverage for emerging attack vectors:

- **A2A Protocol** — Agent-to-agent impersonation, task poisoning, agent card manipulation, context leakage
- **Extended MCP** — Tool poisoning (rug pull), schema injection, server squatting
- **ATLAS October 2025** — Delegation abuse, memory poisoning, observation manipulation

---

## Tool Integrations

AdversaryPilot is **tool-agnostic** — it plans attacks and imports results, but doesn't own execution. This means you keep using the tools you already know.

### garak (NVIDIA)

```bash
# AdversaryPilot recommends a technique and gives you the exact command:
#   Run: garak --model_type openai --probes probes.dan.Dan_6_0
# You run it, then import results:
adversarypilot import garak garak_report.jsonl
```

27 probe-to-technique mappings covering DAN, encoding, hallucination, prompt injection, and more.

### promptfoo

```bash
adversarypilot import promptfoo promptfoo_output.json
```

11 test-type mappings covering jailbreak, hijacking, PII, hallucination, contracts, overreliance, and more.

### Execution Hooks

Every plan entry includes ready-to-run shell commands for supported tools. Copy, paste, execute — then import results back for Bayesian updates.

---

## Compliance & Reporting

### Framework Coverage

| Framework | Controls | Description |
|-----------|----------|-------------|
| **OWASP LLM Top 10** | LLM01–LLM10 | Injection, data leakage, supply chain, output handling, and more |
| **NIST AI RMF** | GOVERN, MAP, MEASURE, MANAGE | Risk identification, measurement, and management subcategories |
| **EU AI Act** | Art. 9, 10, 13, 15, 17, 52, 65, 71 | Risk management, data governance, transparency, accuracy, monitoring |

Reports show per-framework coverage gauges, per-control test status (pass/fail/untested), and prioritized recommendations for untested controls.

### HTML Report Tabs

| Tab | Content |
|-----|---------|
| Executive Summary | Key findings, risk level, trust package, assessment quality score |
| Attack Graph | Force-directed Canvas visualization of technique relationships |
| Layer Analysis | Per-surface risk scores with Wilson confidence intervals and Z-score badges |
| Risk Heatmap | Surface x Goal success rate matrix |
| Technique Details | Full table with scores, results, execution hooks |
| ATLAS Mapping | MITRE ATLAS technique cross-references |
| Compliance | Framework coverage gauges, control status, gap analysis |
| Belief Evolution | Posterior parameter trajectories over campaign steps |
| Statistics | Sensitivity analysis, evidence depth, statistical power |
| Raw Data | Complete JSON export for programmatic analysis |

---

## How AdversaryPilot Compares

|  | AdversaryPilot | [garak](https://github.com/NVIDIA/garak) | [PyRIT](https://github.com/Azure/PyRIT) | [promptfoo](https://github.com/promptfoo/promptfoo) | [HarmBench](https://github.com/centerforaisafety/HarmBench) |
|--|---|---|---|---|---|
| **Focus** | Attack *strategy* | Attack *execution* | Attack *execution* | Eval & red team | Benchmark |
| **Planning** | Bayesian Thompson Sampling | None | Orchestrator scoring | None | None |
| **Adaptive** | Yes (posterior updates) | No | Limited | No | No |
| **Techniques** | 70 (LLM + Agent + AML) | 100+ probes | 20+ strategies | 15+ tests | 18 methods |
| **Compliance** | OWASP + NIST + EU AI Act | None | None | OWASP partial | None |
| **Z-Score Calibration** | Yes (vs benchmarks) | Z-score (reference models) | No | No | Provides baselines |
| **Attack Paths** | Yes (joint probabilities) | No | Multi-turn chains | No | No |
| **Sensitivity Analysis** | Yes (weight perturbation) | No | No | No | No |
| **Meta-Learning** | Yes (cross-campaign) | No | No | No | No |
| **Reports** | Self-contained HTML (10 tabs) | JSONL logs | Notebooks | Web UI + CLI | Leaderboard |
| **Import From** | garak, promptfoo | — | — | — | — |

**AdversaryPilot doesn't compete with these tools — it orchestrates them.** Use garak or promptfoo to execute attacks, import results into AdversaryPilot for strategic analysis, and get the next recommendation.

---

## Citations & References

### Research Foundations

AdversaryPilot builds on published research in adversarial ML and LLM security:

- **MITRE ATLAS** — Adversarial Threat Landscape for AI Systems. MITRE Corporation. [atlas.mitre.org](https://atlas.mitre.org/)
- **HarmBench** — Mazeika et al. "HarmBench: A Standardized Evaluation Framework for Automated Red Teaming and Robust Refusal." *arXiv:2402.04249*, 2024.
- **JailbreakBench** — Chao et al. "JailbreakBench: An Open Robustness Benchmark for Jailbreaking Large Language Models." *arXiv:2404.01318*, 2024.
- **PAIR** — Chao et al. "Jailbreaking Black-Box Large Language Models in Twenty Queries." *arXiv:2310.08419*, 2023.
- **TAP** — Mehrotra et al. "Tree of Attacks: Jailbreaking Black-Box LLMs with Auto-Generated Subtrees." *arXiv:2312.02119*, 2023.
- **GCG** — Zou et al. "Universal and Transferable Adversarial Attacks on Aligned Language Models." *arXiv:2307.15043*, 2023.
- **AutoDAN** — Liu et al. "AutoDAN: Generating Stealthy Jailbreak Prompts on Aligned Large Language Models." *arXiv:2310.04451*, 2023.
- **Crescendo** — Russinovich et al. "Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack." *arXiv:2404.01833*, 2024.
- **Skeleton Key** — Microsoft Threat Intelligence. "Skeleton Key Jailbreak Attack." *Microsoft Security Blog*, 2024.
- **Thompson Sampling** — Russo et al. "A Tutorial on Thompson Sampling." *Foundations and Trends in Machine Learning*, 2018.
- **Wilson Score Interval** — Wilson, E.B. "Probable Inference, the Law of Succession, and Statistical Inference." *JASA*, 1927.

### Compliance Standards

- **OWASP LLM Top 10** — OWASP Foundation. [owasp.org/www-project-top-10-for-large-language-model-applications](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- **NIST AI RMF** — NIST AI 100-1. "Artificial Intelligence Risk Management Framework." [nist.gov/itl/ai-risk-management-framework](https://www.nist.gov/itl/ai-risk-management-framework)
- **EU AI Act** — Regulation (EU) 2024/1689. [eur-lex.europa.eu](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)

### Tools & Frameworks

- **garak** — NVIDIA. Generative AI Red-teaming & Assessment Kit. [github.com/NVIDIA/garak](https://github.com/NVIDIA/garak)
- **PyRIT** — Microsoft. Python Risk Identification Toolkit for GenAI. [github.com/Azure/PyRIT](https://github.com/Azure/PyRIT)
- **promptfoo** — promptfoo. LLM evaluation and red teaming. [github.com/promptfoo/promptfoo](https://github.com/promptfoo/promptfoo)
- **HarmBench** — Center for AI Safety. [github.com/centerforaisafety/HarmBench](https://github.com/centerforaisafety/HarmBench)
- **AgentDojo** — ETH Zurich. Agent security benchmark. [github.com/ethz-spylab/agentdojo](https://github.com/ethz-spylab/agentdojo)
- **Adversarial Robustness Toolbox** — IBM. [github.com/Trusted-AI/adversarial-robustness-toolbox](https://github.com/Trusted-AI/adversarial-robustness-toolbox)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

```bash
# Quick dev setup
git clone https://github.com/aviralsrivastava/AdversaryPilot.git
cd AdversaryPilot
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Responsible Use

AdversaryPilot is designed exclusively for **authorized security testing**, research, and defensive evaluation. By using this tool, you agree to:

- Only test systems you own or have explicit written authorization to test
- Comply with all applicable laws and regulations
- Report discovered vulnerabilities through responsible disclosure
- Not use this tool to cause harm, disrupt services, or compromise systems without authorization

This tool generates attack *plans* and *analysis* — it does not execute attacks autonomously. You are responsible for how you use the recommended techniques.

---

## License

[Apache License 2.0](LICENSE) — Copyright 2025 Aviral Srivastava
