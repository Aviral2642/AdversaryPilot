---
layout: home
title: "AdversaryPilot - Bayesian Attack Planning for LLM & AI Security Testing"
description: "Open-source Bayesian attack planning engine with 70 MITRE ATLAS techniques for LLM, agent, and ML red teaming. Imports garak & promptfoo results."
permalink: /
---

## The Strategic Layer Above Your Attack Tools

Existing tools like garak, promptfoo, and PyRIT excel at *running* attacks. AdversaryPilot answers the harder questions they can't:

<div class="features">
  <div class="feature-card">
    <span class="feature-icon">&#x1f3af;</span>
    <h3>What should I try next?</h3>
    <p>Thompson Sampling explores the most promising attack techniques while balancing exploitation and exploration.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">&#x1f50d;</span>
    <h3>Which layer is weakest?</h3>
    <p>Bayesian posterior analysis identifies the most vulnerable system layer with calibrated confidence intervals.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">&#x1f4ca;</span>
    <h3>Are these results meaningful?</h3>
    <p>Z-score calibration against HarmBench and JailbreakBench baselines - not raw percentages.</p>
  </div>
  <div class="feature-card">
    <span class="feature-icon">&#x1f6e1;</span>
    <h3>Am I meeting compliance?</h3>
    <p>Automated mapping to OWASP LLM Top 10, NIST AI RMF, and EU AI Act with gap analysis.</p>
  </div>
</div>

## Key Capabilities

<div class="features">
  <div class="feature-card">
    <h3>Bayesian Attack Planning</h3>
    <p>Thompson Sampling with correlated arms and benchmark-calibrated priors. The planner learns from every test result and recommends increasingly targeted techniques.</p>
  </div>
  <div class="feature-card">
    <h3>70 MITRE ATLAS Techniques</h3>
    <p>LLM jailbreaks (DAN, PAIR, TAP, GCG, Crescendo), prompt injection, agent exploitation (MCP poisoning, A2A impersonation), and classical AML attacks.</p>
  </div>
  <div class="feature-card">
    <h3>Compliance Mapping</h3>
    <p>Every technique maps to OWASP LLM Top 10, NIST AI RMF, and EU AI Act. Reports show per-framework coverage and untested controls.</p>
  </div>
  <div class="feature-card">
    <h3>Tool Integrations</h3>
    <p>Import results from garak (27 probe mappings) and promptfoo (11 test mappings). Execution hooks generate ready-to-run shell commands.</p>
  </div>
  <div class="feature-card">
    <h3>Z-Score Calibration</h3>
    <p>Results calibrated against HarmBench and JailbreakBench benchmarks, reported as standard deviations from baseline with statistical significance.</p>
  </div>
  <div class="feature-card">
    <h3>Self-Contained HTML Reports</h3>
    <p>10 interactive tabs: attack graphs, compliance dashboards, belief evolution, risk heatmaps. Zero dependencies - open in any browser.</p>
  </div>
</div>

## How the Planner Works

<div class="pipeline">
  <div class="pipeline-step">
    <span class="step-name">Target Profile</span>
    <span class="step-desc">YAML definition</span>
  </div>
  <span class="pipeline-arrow">&#x2192;</span>
  <div class="pipeline-step">
    <span class="step-name">Hard Filters</span>
    <span class="step-desc">Access, domain, target</span>
  </div>
  <span class="pipeline-arrow">&#x2192;</span>
  <div class="pipeline-step">
    <span class="step-name">7-Dim Scorer</span>
    <span class="step-desc">Compatibility, fit, risk</span>
  </div>
  <span class="pipeline-arrow">&#x2192;</span>
  <div class="pipeline-step">
    <span class="step-name">Thompson Sample</span>
    <span class="step-desc">Beta posteriors + priors</span>
  </div>
  <span class="pipeline-arrow">&#x2192;</span>
  <div class="pipeline-step">
    <span class="step-name">Ranked Plan</span>
    <span class="step-desc">Rationale, hooks, Z-scores</span>
  </div>
</div>

## Quick Start

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+. Only 4 dependencies: `pydantic`, `typer`, `rich`, `pyyaml`.

```bash
adversarypilot plan target.yaml              # Generate ranked attack plan
adversarypilot campaign new target.yaml      # Start adaptive campaign
adversarypilot import garak report.jsonl     # Import tool results
adversarypilot campaign next <id>            # Get Bayesian recommendations
adversarypilot report <id>                   # Generate HTML report
```

## Explore the Documentation

<div class="docs-grid">
  <a href="{{ '/what-is-adversarypilot/' | relative_url }}">
    <div class="doc-title">What is AdversaryPilot?</div>
    <div class="doc-desc">How Bayesian attack planning works and how it compares to garak, PyRIT, and promptfoo.</div>
  </a>
  <a href="{{ '/ai-red-team-strategy/' | relative_url }}">
    <div class="doc-title">AI Red Team Strategy</div>
    <div class="doc-desc">Building a systematic, compliance-driven AI red team methodology with two-phase campaigns.</div>
  </a>
  <a href="{{ '/mitre-atlas-ai-red-teaming-planner/' | relative_url }}">
    <div class="doc-title">MITRE ATLAS Red Teaming Planner</div>
    <div class="doc-desc">Full catalog of 70 ATLAS-aligned techniques with compliance cross-mapping.</div>
  </a>
  <a href="{{ '/adversarial-attack-sequencing/' | relative_url }}">
    <div class="doc-title">Adversarial Attack Sequencing</div>
    <div class="doc-desc">Multi-stage attack paths with beam search and joint success probabilities.</div>
  </a>
  <a href="{{ '/garak-results-analysis/' | relative_url }}">
    <div class="doc-title">Analyzing Garak Results</div>
    <div class="doc-desc">Import garak JSONL output for Bayesian analysis, Z-score calibration, and compliance reporting.</div>
  </a>
  <a href="{{ '/promptfoo-attack-planning/' | relative_url }}">
    <div class="doc-title">Promptfoo Attack Planning</div>
    <div class="doc-desc">Plan and analyze promptfoo red team tests with execution hooks and adaptive recommendations.</div>
  </a>
</div>
