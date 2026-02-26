---
layout: page
title: "AI Red Team Strategy: Bayesian Planning for LLM Security Testing"
description: "Learn AI red team strategy with Bayesian attack planning. Prioritize 70 ATLAS-aligned techniques across LLM, agent, and ML surfaces with AdversaryPilot."
permalink: /ai-red-team-strategy/
---

# AI Red Team Strategy: From Ad Hoc Testing to Bayesian Planning

AI red teaming is evolving from "try a few jailbreaks and write a report" to a structured discipline with measurable coverage, statistical rigor, and compliance alignment. This guide explains how to build a systematic AI red team strategy using Bayesian attack planning.

## The State of AI Red Teaming Today

Most AI security teams face the same problems:

**No prioritization framework.** With dozens of known attack techniques across LLM jailbreaks, prompt injection, agent exploitation, and classical adversarial ML, teams default to running whatever they've seen in blog posts or benchmarks. There is no systematic way to decide which technique to try next against a specific target.

**No coverage measurement.** After running 10 tests, how do you know what you've covered? Which OWASP LLM Top 10 controls were tested? Which NIST AI RMF subcategories have gaps? Without mapping tests to compliance frameworks, "we ran some red team tests" is the best you can report.

**No statistical calibration.** A 40% attack success rate sounds concerning - but is it? Without calibrating against benchmark baselines (HarmBench, JailbreakBench), raw success rates are uninterpretable. AdversaryPilot reports results as Z-scores: "1.2 sigma above HarmBench baseline" is actionable; "40% ASR" is not.

**No adaptive learning.** Running the same set of tests against every target ignores what you've already learned. If system prompt extraction succeeded, the planner should prioritize techniques that exploit the extracted knowledge. If jailbreaks failed, it should shift to other surfaces.

## Why Strategy Matters More Than Tool Choice

The tools are good. [Garak](https://github.com/NVIDIA/garak) has 100+ probes. [PyRIT](https://github.com/Azure/PyRIT) has multi-turn orchestration. [Promptfoo](https://github.com/promptfoo/promptfoo) has evaluation pipelines. What's missing is the strategic layer that answers:

- Which of these tools should I use first?
- Which probes/tests should I run?
- In what order?
- When should I stop?
- What can I tell the CISO?

[AdversaryPilot]({{ '/what-is-adversarypilot/' | relative_url }}) is that strategic layer.

## The Two-Phase Campaign Model

AdversaryPilot organizes red team engagements into two phases that mirror real-world methodology:

### Phase 1: Probe (Exploration)

The goal is **broad coverage** across attack surfaces. Thompson Sampling naturally favors uncertain techniques - those with wide posteriors where the planner doesn't yet have data. This drives exploration:

- Test across all 4 surfaces: model, data, retrieval, tool/action
- Try techniques from different families (jailbreaks, injection, extraction, agent exploitation)
- Establish baseline success rates
- Map initial compliance coverage

### Phase 2: Exploit (Exploitation)

Once weaknesses are discovered, the planner shifts to **deep exploitation**. Posteriors narrow as data accumulates, and Thompson Sampling increasingly favors techniques with proven success:

- Chain techniques that build on discovered weaknesses
- Increase testing depth on vulnerable surfaces
- Fill compliance coverage gaps
- Generate statistically significant results

The transition happens automatically - no manual phase switching required.

## Bayesian Prioritization: Exploration vs. Exploitation

The core of AdversaryPilot's strategy is Thompson Sampling with correlated arms:

1. **Sample** from each technique's Beta(alpha, beta) posterior
2. **Rank** by sampled values combined with the 7-dimension compatibility score
3. **Recommend** the top techniques with rationale and execution hooks
4. **Update** posteriors after observing results

The 7 scoring dimensions ensure recommendations are relevant to the specific target:

| Dimension | What It Measures |
|-----------|-----------------|
| Compatibility | Target type match (chatbot, RAG, agent, etc.) |
| Access Fit | Required vs. available access level |
| Goal Alignment | How well the technique serves stated attack goals |
| Defense Bypass | Likelihood of evading known defenses |
| Signal Gain | Information value of the test result |
| Cost Penalty | Query budget and time consumption |
| Detection Risk | Probability of triggering alerts |

## Coverage Across Attack Surfaces

A common blind spot in AI red teaming is testing only the LLM layer. Modern AI systems have multiple attack surfaces:

| Surface | Example Techniques | Often Missed? |
|---------|-------------------|---------------|
| **Model** | Jailbreaks, adversarial examples, model extraction | No |
| **Data** | RAG poisoning, training data extraction, clean-label backdoors | Yes |
| **Retrieval** | Indirect prompt injection via retrieved documents | Yes |
| **Tool/Action** | MCP poisoning, A2A impersonation, delegation abuse | Yes |

AdversaryPilot's [70-technique catalog]({{ '/mitre-atlas-ai-red-teaming-planner/' | relative_url }}) covers all surfaces, and the planner explicitly tracks surface-level coverage to avoid blind spots.

<img src="{{ '/screenshots/heatmap.png' | relative_url }}" alt="Attack surface risk heatmap showing success rates across surfaces and goals">

## Compliance-Driven Red Teaming

Every technique in AdversaryPilot maps to three compliance frameworks:

- **OWASP LLM Top 10** (LLM01–LLM10) - Injection, data leakage, supply chain, output handling
- **NIST AI RMF** (GOVERN, MAP, MEASURE, MANAGE) - Risk identification, measurement, and management
- **EU AI Act** (Articles 9, 10, 13, 15, etc.) - Risk management, transparency, accuracy

This transforms red teaming from "we tested some attacks" to "we've covered 78% of OWASP LLM controls, with gaps in LLM07 (Insecure Plugin Design) and LLM09 (Overreliance)."

Reports show per-framework coverage gauges and prioritized recommendations for untested controls - exactly what procurement and audit teams need.

## Building a Red Team Campaign

Here's a concrete workflow using AdversaryPilot:

```bash
# 1. Define the target
cat > target.yaml <<EOF
schema_version: "1.0"
name: Production Chatbot
target_type: chatbot
access_level: black_box
goals: [jailbreak, extraction]
constraints:
  max_queries: 500
  stealth_priority: moderate
defenses:
  has_moderation: true
  has_input_filtering: true
EOF

# 2. Create an adaptive campaign
adversarypilot campaign new target.yaml --name "q1-assessment"

# 3. Get initial recommendations
adversarypilot campaign next <campaign-id>

# 4. Execute recommended techniques with garak/promptfoo
garak --model_type openai --probes probes.dan.Dan_6_0

# 5. Import results
adversarypilot import garak garak_report.jsonl

# 6. Get updated recommendations (posteriors have shifted)
adversarypilot campaign next <campaign-id>

# 7. Repeat steps 4-6 until coverage goals are met

# 8. Generate the defender report
adversarypilot report <campaign-id>
```

## Sensitivity Analysis: Validating Your Strategy

How do you know the planner's recommendations aren't artifacts of arbitrary weight choices? AdversaryPilot includes a **sensitivity analysis** that perturbs each scoring weight by +/-20% and measures rank stability using Kendall tau correlation.

If a small weight change dramatically reshuffles the technique ranking, the planner warns you. This ensures you can trust the recommendations.

<img src="{{ '/screenshots/statistics.png' | relative_url }}" alt="Sensitivity analysis showing evidence depth and statistical power">

## Meta-Learning Across Campaigns

When you run multiple campaigns against similar targets, AdversaryPilot's meta-learning system transfers learned posteriors. A new campaign against a chatbot with moderation can warm-start from the posteriors of your previous chatbot campaigns, weighted by target similarity (Jaccard distance over target attributes).

This means your second assessment is smarter than your first.

<img src="{{ '/screenshots/belief-evolution.png' | relative_url }}" alt="Bayesian belief evolution showing posterior parameter trajectories over campaign steps">

## Related Pages

- [What is AdversaryPilot?]({{ '/what-is-adversarypilot/' | relative_url }}) - How the Bayesian planner works
- [Adversarial Attack Sequencing]({{ '/adversarial-attack-sequencing/' | relative_url }}) - Multi-stage attack paths
- [MITRE ATLAS Red Teaming Planner]({{ '/mitre-atlas-ai-red-teaming-planner/' | relative_url }}) - Full 70-technique catalog
- [Analyzing Garak Results]({{ '/garak-results-analysis/' | relative_url }}) - Import and analyze garak output
