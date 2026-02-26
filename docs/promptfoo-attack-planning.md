---
layout: page
title: "Promptfoo Attack Planning with AdversaryPilot | Strategic LLM Testing"
description: "Plan and analyze promptfoo red team tests with AdversaryPilot. 11 test mappings, Bayesian prioritization, execution hooks, and compliance analysis for promptfoo outputs."
permalink: /promptfoo-attack-planning/
---

# Promptfoo Attack Planning with AdversaryPilot

## What is Promptfoo?

[Promptfoo](https://github.com/promptfoo/promptfoo) is an open-source LLM evaluation and red teaming framework. It lets you define test cases in YAML, run them against LLM providers, and evaluate results using configurable assertion strategies. Promptfoo supports jailbreak testing, PII detection, hallucination checks, hijacking tests, and more.

Promptfoo excels at **defining and running structured tests**. What it does not provide is:

- A prioritization engine that tells you which tests to run first
- Bayesian learning that adapts recommendations based on results
- Z-score calibration against published benchmarks
- Compliance framework mapping (OWASP LLM Top 10, NIST AI RMF, EU AI Act)
- Multi-session campaign management with posterior persistence

AdversaryPilot adds this strategic layer on top of promptfoo.

## Why You Need a Planner Above Promptfoo

Consider a typical promptfoo red team configuration:

```yaml
# promptfoo config
tests:
  - type: jailbreak
  - type: hijacking
  - type: pii
  - type: hallucination
```

This runs 4 test types. But there are at least 15 test types in promptfoo and 70 techniques in AdversaryPilot's catalog. Questions that promptfoo cannot answer:

- **Which 4 tests should you run?** If the target is a RAG chatbot with moderation, hijacking tests and PII extraction are high-value. If it's a code assistant, contract compliance and overreliance are more relevant.
- **In what order?** Running system prompt extraction before jailbreak tests provides information that makes later tests more targeted.
- **When are you done?** After running 4 test types, have you covered the OWASP LLM Top 10? Which controls are untested?

AdversaryPilot's [Bayesian planner]({{ '/what-is-adversarypilot/' | relative_url }}) answers these by scoring all available techniques against the target profile and recommending the optimal sequence.

## How AdversaryPilot Integrates with Promptfoo

The integration works in two directions:

### Direction 1: AdversaryPilot Plans → Promptfoo Executes

When AdversaryPilot generates an attack plan, each recommended technique includes **execution hooks** - ready-to-run commands for supported tools. For promptfoo-compatible techniques, the hook is a promptfoo CLI command:

```bash
adversarypilot plan target.yaml
```

Output includes:

```
#3  Direct Prompt Injection (AP-TX-LLM-INJECT-DIRECT)
    Score: 2.87  |  Prior ASR: 0.38 ± 0.22
    strong fit for chatbot targets; tests LLM01 (OWASP)
    Run: promptfoo eval --config hijacking_config.yaml
```

You copy the command, run it, and import the results back.

### Direction 2: Promptfoo Results → AdversaryPilot Analyzes

After running promptfoo tests, import the JSON output for Bayesian analysis:

```bash
promptfoo eval --output results.json
adversarypilot import promptfoo results.json
```

## 11 Promptfoo Test-to-Technique Mappings

AdversaryPilot maps 11 promptfoo test types to its ATLAS-aligned technique catalog:

| Promptfoo Test Type | AdversaryPilot Technique(s) | ATLAS Ref | OWASP LLM |
|--------------------|-----------------------------|-----------|------------|
| `jailbreak` | DAN Jailbreak, Persona-based Jailbreak, Crescendo | AML.T0051 | LLM01 |
| `hijacking` | Direct Prompt Injection, Goal Hijacking | AML.T0051 | LLM01 |
| `pii` | Training Data Extraction, Data Exfiltration | AML.T0024 | LLM06 |
| `hallucination` | Hallucination Elicitation | AML.T0048 | LLM09 |
| `overreliance` | Overreliance Exploitation | AML.T0048 | LLM09 |
| `contracts` | Contract Compliance Bypass | AML.T0051 | LLM07 |
| `harmful:hate` | Jailbreak (Harmful Content) | AML.T0051 | LLM01 |
| `harmful:violent` | Jailbreak (Harmful Content) | AML.T0051 | LLM01 |
| `harmful:sexual` | Jailbreak (Harmful Content) | AML.T0051 | LLM01 |
| `harmful:self-harm` | Jailbreak (Harmful Content) | AML.T0051 | LLM01 |
| `harmful:illegal` | Jailbreak (Harmful Content) | AML.T0051 | LLM01 |

## Planning Before Testing: Getting the Right Sequence

Instead of guessing which promptfoo tests to run, let AdversaryPilot plan the sequence:

```bash
# Define your target
cat > target.yaml <<EOF
schema_version: "1.0"
name: Customer Support Bot
target_type: chatbot
access_level: black_box
goals: [jailbreak, extraction, hijacking]
constraints:
  max_queries: 300
defenses:
  has_moderation: true
  has_input_filtering: true
  has_output_filtering: true
EOF

# Get a ranked plan
adversarypilot plan target.yaml
```

The planner considers the target's defenses, goals, and access level to recommend the most effective test sequence. For a chatbot with moderation and filtering, it might recommend:

1. System Prompt Extraction (high signal, low cost)
2. Encoding Bypass probes (test filter coverage)
3. Jailbreak tests (informed by what was learned above)
4. PII/extraction tests
5. Hijacking tests

Each recommendation includes the promptfoo command to execute it.

## Importing Promptfoo Results

```bash
# Run promptfoo
promptfoo eval --config red-team-config.yaml --output results.json

# Import into AdversaryPilot
adversarypilot import promptfoo results.json
```

The importer processes each test result:

1. Maps the promptfoo test type to AdversaryPilot technique(s)
2. Extracts pass/fail status and confidence scores
3. Creates `AttemptResult` and `EvaluationResult` records
4. Updates the campaign's Bayesian posteriors
5. Triggers family correlation updates

## Bayesian Updates from Promptfoo Data

After importing promptfoo results, the planner's behavior changes:

**If jailbreak tests succeeded**: The posterior for jailbreak techniques shifts toward higher success probability. Family correlation boosts related techniques (Crescendo, PAIR, encoding bypass). The planner may recommend deeper exploitation of the jailbreak surface.

**If jailbreak tests failed**: The posterior shifts toward lower success probability. The planner pivots to other surfaces - agent exploitation, data extraction, or indirect prompt injection - that haven't been tested yet.

**If PII tests revealed data leakage**: The posterior for extraction techniques updates. The planner may recommend training data extraction or embedding inversion to probe the leakage further.

This adaptive behavior is the core value proposition: promptfoo runs the tests, AdversaryPilot learns from the results and plans what comes next.

## Compliance Coverage from Promptfoo Tests

Every promptfoo test, once mapped to AdversaryPilot techniques, inherits compliance framework references:

| Promptfoo Test | OWASP LLM | NIST AI RMF | EU AI Act |
|---------------|-----------|-------------|-----------|
| jailbreak | LLM01 | MAP 1.1 | Art. 9, Art. 15 |
| hijacking | LLM01 | MAP 1.5 | Art. 9 |
| pii | LLM06 | MEASURE 2.6 | Art. 10 |
| hallucination | LLM09 | MEASURE 2.3 | Art. 13 |
| contracts | LLM07 | GOVERN 1.4 | Art. 17 |

After importing, the compliance dashboard shows exactly which OWASP LLM Top 10 controls are covered by your promptfoo tests and which still need attention. This transforms promptfoo output from "5 tests passed, 3 failed" into "we've covered LLM01, LLM06, and LLM09; gaps remain in LLM02, LLM03, LLM04, LLM05, LLM07, LLM08, and LLM10."

<img src="{{ '/screenshots/technique-details.png' | relative_url }}" alt="Technique details showing scores, results, and execution hooks">

## Step-by-Step Workflow: Promptfoo + AdversaryPilot

```bash
# 1. Create a campaign
adversarypilot campaign new target.yaml --name "promptfoo-assessment"

# 2. Get initial recommendations with promptfoo execution hooks
adversarypilot campaign next <campaign-id>

# 3. Run recommended promptfoo tests
promptfoo eval --config jailbreak-config.yaml --output jailbreak-results.json

# 4. Import results
adversarypilot import promptfoo jailbreak-results.json

# 5. Get updated recommendations (posteriors have shifted)
adversarypilot campaign next <campaign-id>

# 6. Run next batch of promptfoo tests
promptfoo eval --config extraction-config.yaml --output extraction-results.json

# 7. Import and repeat
adversarypilot import promptfoo extraction-results.json

# 8. Generate compliance-ready report
adversarypilot report <campaign-id>
```

## What You Get That Promptfoo Alone Does Not Provide

| Capability | Promptfoo Alone | Promptfoo + AdversaryPilot |
|-----------|----------------|---------------------------|
| Define and run tests | Yes | Yes (with execution hooks) |
| Which tests to run next | Manual choice | Bayesian recommendation |
| Test sequencing | Manual ordering | [Attack path analysis]({{ '/adversarial-attack-sequencing/' | relative_url }}) |
| Statistical calibration | Pass/fail counts | Z-score vs HarmBench/JailbreakBench |
| Compliance mapping | None | OWASP + NIST + EU AI Act |
| Adaptive learning | None | Thompson Sampling with posterior updates |
| Cross-campaign memory | None | Meta-learning across similar targets |
| Report format | Web UI, CLI output | 10-tab HTML report |

## Related Pages

- [Analyzing Garak Results]({{ '/garak-results-analysis/' | relative_url }}) - The other supported tool integration
- [What is AdversaryPilot?]({{ '/what-is-adversarypilot/' | relative_url }}) - How the Bayesian planner works
- [Adversarial Attack Sequencing]({{ '/adversarial-attack-sequencing/' | relative_url }}) - Multi-stage attack paths
- [MITRE ATLAS Red Teaming Planner]({{ '/mitre-atlas-ai-red-teaming-planner/' | relative_url }}) - Full ATLAS-aligned technique catalog
