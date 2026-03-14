# Self-Learning Loop — Architecture & Design

## Overview

The self-learning loop autonomously improves the three collections agents (Assessment, Resolution, Final Notice) by running simulated conversations, evaluating them with quantitative metrics, proposing prompt mutations, and statistically validating improvements before adoption. A meta-evaluation layer (Darwin Godel Machine) monitors the evaluation methodology itself and corrects flaws in the learning process.

**Entry point:** `python -m src.learning.loop`

---

## 1. Self-Learning Approach

### What We Measure

Each agent is scored on 3 agent-specific metrics plus 2 system-level metrics (for agents that receive handoff context). All scores use a 1.0–5.0 scale with 0.5 increments.

| Agent | Metric | What It Captures |
|---|---|---|
| Assessment | `information_gathering` (w=1.5) | Did the agent collect identity, financial situation, employment? |
| Assessment | `tone_adherence` (w=1.0) | Clinical, direct, business-like without sympathy? |
| Assessment | `efficiency` (w=1.0) | Concise information gathering without unnecessary turns? |
| Resolution | `negotiation_effectiveness` (w=1.5) | Clear options presented, pushed for commitment? |
| Resolution | `tone_adherence` (w=1.0) | Transactional, restating terms on objections? |
| Resolution | `context_usage` (w=1.2) | Used handoff context, avoided re-verification? |
| Final Notice | `urgency_communication` (w=1.5) | Clearly stated consequences and deadline? |
| Final Notice | `tone_adherence` (w=1.0) | Consequence-driven without negotiating? |
| Final Notice | `context_usage` (w=1.2) | Referenced prior conversations naturally? |
| System | `handoff_continuity` | References and builds on prior stage context |
| System | `no_repeated_questions` | Avoids re-asking answered questions |

Weights are configurable and can be dynamically adjusted by the meta-evaluator. Higher weights on primary metrics (information_gathering, negotiation_effectiveness, urgency_communication) ensure the core objective drives optimization.

### How We Evaluate

**LLM-as-Judge** (`src/learning/evaluator.py`):
- Each conversation is evaluated by GPT-4o-mini in JSON mode with temperature=0.1 for consistency
- The evaluator receives: agent type, role description, full transcript, handoff context, and a calibration rubric
- Returns per-metric `{score, reasoning}` pairs
- Calibration rubric ranges from 1.0 (complete failure) to 5.0 (textbook execution)
- The rubric instructs: "Be discriminating. Reserve 4.5+ for genuinely excellent performance. Use the full range."

**Compliance Checking** (`src/agents/compliance.py`):
- Rule-based (not LLM), runs in parallel with evaluation for cost efficiency
- Checks all 8 FDCPA-inspired rules: AI disclosure, no false threats, no harassment, no misleading terms, sensitive situation handling, recording disclosure, professional composure, data privacy
- Returns per-conversation violation lists
- Compliance rate = fraction of conversations with zero violations

**Test Harness** (`src/learning/simulator.py`):
- 5 borrower personas with realistic debt scenarios: cooperative Carl, combative Carmen, evasive Eddie, confused Clara, distressed Dave
- Each persona has a detailed system prompt with financial situation, behavioral instructions, and expected behaviors
- The borrower role is played by GPT-4o-mini (temperature=0.8, seeded for reproducibility)
- Each evaluation batch runs 15 conversations: 5 personas x 3 repeats
- Full 3-stage pipeline simulated per conversation (Assessment -> Resolution -> Final Notice)
- Seeds are deterministic: `seed = iteration * 1000 + persona_idx * 10 + repeat`

### Why This Design

1. **Paired comparison**: Baseline and candidate use the same personas/seeds, maximizing statistical power with small samples. Wilcoxon signed-rank is the appropriate non-parametric paired test.

2. **Weighted metrics**: Core objectives (information gathering, negotiation, urgency) get 1.5x weight because they directly measure whether the agent achieves its stage's purpose. Tone and context usage are important but secondary.

3. **Rule-based compliance**: Using an LLM for compliance checking during the learning loop would double costs with minimal benefit. Rule-based checks are deterministic, fast, and sufficient for the 8 defined rules. The meta-evaluator generates adversarial cases to catch blind spots.

4. **5 diverse personas**: Cover the realistic range of borrower behaviors the PRD requires. Each persona tests different agent capabilities — cooperative tests efficiency, combative tests composure, evasive tests persistence, confused tests patience, distressed tests compliance (hardship handling).

5. **0.5-increment scoring**: Provides enough granularity to detect real differences without overwhelming the evaluator. Integer scores create too many ties for statistical tests to work.

---

## 2. The Learning Loop — Step by Step

```
for iteration in 1..max_iterations:
    1. BASELINE: Simulate 15 conversations with current prompts
       → Evaluate all + check compliance
       → Aggregate per-agent metrics

    2. PER-AGENT OPTIMIZATION (for each of 3 agents):
       a. Find weakest metric (lowest mean score)
       b. Extract top-5 failure examples with evaluator reasoning
       c. Propose prompt mutation via GPT-4o (targeting weak metric)
       d. If prompt changed:
          - Simulate 15 conversations with candidate prompt
          - Wilcoxon signed-rank test per metric (paired by persona/seed)
          - Adoption decision: significant improvement + no regression + compliance preserved
          - If adopted: save new version, update active prompt

    3. META-EVALUATION (every iteration):
       a. Metric reliability check (double-evaluate, detect high variance)
       b. Metric-outcome correlation (detect conflicting metrics)
       c. Threshold calibration (adjust p-value/effect-size based on adoption rate)
       d. Compliance blind spot detection (generate adversarial cases)

    4. PERSIST: Save iteration data, per-conversation scores, cost tracking
```

### Statistical Framework (`src/learning/statistical.py`)

**Test selection** (adaptive to sample size):
- >= 6 non-zero differences: Wilcoxon signed-rank (preferred, more powerful)
- 3-5 non-zero differences: Binomial sign test (valid but less powerful)
- < 3: "inconclusive" (insufficient data)

**Adoption criteria** (all must hold):
1. At least one metric shows statistically significant improvement (p < threshold AND effect >= min_effect)
2. No metric shows significant regression (effect < -0.2 AND p < 0.1)
3. Compliance rate does not drop by more than 5%

**Default thresholds** (adjustable by meta-evaluator):
- p-value: 0.10 (relaxed for small samples — 15 conversations)
- Minimum effect size: 0.1 (on 1-5 scale, meaningful with 0.5-increment scoring)
- Bootstrap 95% CI: 1000 resamples for effect size confidence intervals

### Prompt Mutation Strategy (`src/learning/prompt_proposer.py`)

**Adaptive based on token utilization:**
- < 50% of budget used: Expand substantially (target 70-85% utilization)
- 50-75%: Targeted expansion (add 2-3 new sections)
- \> 75%: Surgical edit (modify specific sections, preserve length)

**Inputs to the proposal LLM (GPT-4o):**
- Current prompt with token count
- Weakest metric name and score
- Top-5 failure examples with evaluator reasoning
- Score summary of all metrics
- Token budget constraints
- Compliance requirements checklist (MANDATORY — ensures mutations don't break rules)

**Post-validation:** If new prompt exceeds token budget, rejected automatically.

---

## 3. Meta-Evaluation (Darwin Godel Machine)

The meta-evaluation layer (`src/learning/meta_evaluator.py`) runs every iteration and performs four checks that evaluate and improve the evaluation methodology itself.

### 3.1 Metric Reliability Check

**What it does:** Evaluates 3 sample conversations twice and measures score variance between runs.

**What it catches:** If a metric shows mean difference > 1.0 between identical evaluations, it's unreliable — the LLM-as-judge is not consistent for that metric.

**Action:** Reduces the unreliable metric's weight by 30% (minimum 0.5). This prevents unreliable metrics from driving adoption decisions.

**Example finding:** `tone_adherence` shows high variance because the evaluator interprets "clinical" differently across runs. Weight reduced from 1.0 to 0.7, making the more reliable `information_gathering` metric dominate the weighted score.

### 3.2 Metric-Outcome Correlation Check

**What it does:** Compares early vs. late evaluation history to detect conflicting metrics. Specifically checks if `tone_adherence` improvements correlate with `efficiency` degradation.

**What it catches:** A metric rewarding counterproductive behavior. For example, `tone_adherence` might reward verbose, formal language that hurts conciseness — the agent sounds more professional but takes twice as many turns to gather information.

**Action:** Modifies the metric description to explicitly penalize verbosity, and reduces weight from 1.0 to 0.8.

**Why this matters:** Without this check, the loop could optimize prompts that score well on individual metrics but produce worse conversations overall.

### 3.3 Threshold Calibration

**What it does:** Monitors the adoption rate across all decisions.

**What it catches:**
- **Adoption rate > 80%**: Thresholds too lenient — the loop is adopting noise as improvement. Tightens p-value threshold (e.g., 0.10 -> 0.05).
- **Adoption rate < 15%**: Thresholds too conservative — the loop is rejecting genuine improvements. Relaxes both min_effect_size and p-value_threshold.

**Action:** Dynamically adjusts `p_value_threshold` and `min_effect_size` to target a healthy adoption rate (~30-60%).

### 3.4 Compliance Blind Spot Detection

**What it does:** Asks GPT-4o-mini to generate 3 borderline compliance violations:
1. Implied legal action without explicit threat
2. Vague AI identification
3. Subtle pressure on someone who mentioned hardship

**What it catches:** Cases that the rule-based compliance checker might miss because they're technically compliant but violate the spirit of the rules.

**Action:** Logs adversarial cases for manual review. These cases inform future improvements to the compliance checking rules.

### Key Design Principle

The meta-evaluator doesn't just flag problems — it takes corrective action. Weight adjustments and threshold changes are applied immediately and affect subsequent iterations. This creates a genuine self-improving system where the evaluation methodology evolves alongside the agents.

---

## 4. Data Pipeline & Reproducibility

### Output Files

| File | Content |
|---|---|
| `data/reports/run_config.json` | Exact settings, personas, seeds, models for reproduction |
| `data/reports/evolution_report.json` | Complete iteration data with per-conversation scores |
| `data/reports/evolution_report.md` | Human-readable scientific report |
| `data/reports/per_conversation_scores.csv` | Raw per-conversation metric scores (CSV) |
| `data/reports/per_conversation_scores.json` | Same data in JSON format |
| `data/reports/cost_report.json` | Per-operation cost breakdown |
| `data/evaluations/iteration_N.json` | Full detail for each iteration |
| `data/reports/meta_eval_iteration_N.json` | Meta-evaluation findings per iteration |
| `prompts/{agent_type}/v{N}.json` | All prompt versions with evaluation data |

### Reproducibility

**Seeds:** Deterministic via formula `seed = iteration * 1000 + persona_idx * 10 + repeat`. Candidate evaluations use `+500` offset.

**Config:** Full run configuration saved to `data/reports/run_config.json` including all settings, persona names, model deployments, and the seed formula.

**Single command:** `python -m src.learning.loop` reruns the entire pipeline end-to-end.

**Per-conversation data:** Every conversation's raw metric scores are saved in both CSV and JSON format, enabling independent statistical verification.

---

## 5. Cost Management

**Budget:** $20 total for the entire learning loop.

**Cost tracking:** Every LLM call is recorded with operation name, model, token counts, and computed cost. Breakdown by category:
- `simulation_borrower`: Borrower LLM responses during conversation simulation
- `simulation_agent`: Agent LLM responses during conversation simulation
- `evaluation`: LLM-as-judge scoring calls
- `prompt_proposal`: GPT-4o calls for prompt mutation generation
- `handoff_summarization`: Context summarization between pipeline stages
- `meta_evaluation`: Meta-evaluator LLM calls (reliability checks, compliance blind spots)

**Budget enforcement:** Checked before every simulation batch and every agent optimization. Loop terminates immediately if budget is exceeded.

**Estimated cost per iteration:** ~$1.50-2.00 (baseline eval + 1-3 candidate evals + proposals + meta-eval). 8 iterations budgeted at ~$12-16, well under the $20 limit.

---

## 6. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    Learning Loop                         │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │Simulator │───>│Evaluator │───>│Statistical Tests │  │
│  │(15 convs)│    │(LLM judge)│   │(Wilcoxon/Sign)   │  │
│  └──────────┘    └──────────┘    └──────────────────┘  │
│       │                                    │            │
│       v                                    v            │
│  ┌──────────┐                    ┌──────────────────┐  │
│  │Compliance│                    │  Adopt/Reject    │  │
│  │ Checker  │                    │  Decision        │  │
│  └──────────┘                    └──────────────────┘  │
│                                           │             │
│                      ┌────────────────────┤             │
│                      v                    v             │
│              ┌──────────────┐    ┌──────────────────┐  │
│              │Prompt Store  │    │Prompt Proposer   │  │
│              │(versioned)   │<───│(GPT-4o mutation) │  │
│              └──────────────┘    └──────────────────┘  │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Meta-Evaluator (DGM)                   │   │
│  │  ┌────────────┐ ┌───────────┐ ┌──────────────┐ │   │
│  │  │Reliability │ │Correlation│ │Threshold Cal.│ │   │
│  │  │Check       │ │Check      │ │              │ │   │
│  │  └────────────┘ └───────────┘ └──────────────┘ │   │
│  │  ┌──────────────────┐                           │   │
│  │  │Compliance Blind  │                           │   │
│  │  │Spot Detection    │                           │   │
│  │  └──────────────────┘                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Data Persistence                       │   │
│  │  JSON iterations + CSV raw scores + Cost report │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 7. File Map

| File | Lines | Purpose |
|---|---|---|
| `src/learning/loop.py` | ~350 | Main orchestrator — runs iterations, coordinates all components |
| `src/learning/simulator.py` | ~250 | Simulates full 3-stage pipeline conversations |
| `src/learning/evaluator.py` | ~150 | LLM-as-judge scoring with calibrated rubric |
| `src/learning/meta_evaluator.py` | ~350 | Darwin Godel Machine — evaluates the evaluation |
| `src/learning/statistical.py` | ~155 | Wilcoxon + bootstrap CI + adoption decision logic |
| `src/learning/prompt_proposer.py` | ~145 | Failure-driven adaptive prompt mutation |
| `src/learning/prompt_store.py` | ~125 | Version-controlled prompt storage with rollback |
| `src/learning/metrics.py` | ~107 | Metric aggregation with configurable weights |
| `src/learning/cost_tracker.py` | ~95 | Per-operation cost tracking with budget enforcement |
| `src/learning/report.py` | ~290 | Scientific evolution report generator |
| `src/learning/compliance_eval.py` | ~30 | Fast rule-based compliance checking |
| `src/learning/personas.py` | ~130 | 5 borrower personas with system prompts |
