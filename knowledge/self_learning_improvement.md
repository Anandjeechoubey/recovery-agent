# Fix Self-Learning Loop: KeyErrors, Low Adoption Rate, Hardship Bias

## Context

The self-learning loop currently faces three critical issues:

- **KeyErrors during prompt rendering:** The LLM proposes prompts with template variables (e.g., `{employment_status}`, `{settlement_amount}`) that do not exist in `_render_system_prompt()`.
- **8.3% adoption rate (2/24):** Statistical thresholds are too strict for the sample size, and the per-metric significance requirement is too granular.
- **Hardship program over-representation:** 40% of personas are hardship-focused, the outcome classifier is too liberal, and agent prompts aggressively trigger hardship.

---

## Fix 1: KeyErrors in Prompt Rendering

**Target Files:** `base.py`, `prompt_proposer.py`

### 1a. Make `_render_system_prompt()` resilient

- **Location:** `base.py` (lines 51-62)
- **Action:** Switch from `.format()` to `.format_map()` using a `defaultdict` that returns `{key}` for unknown keys. This ensures unknown variables pass through harmlessly instead of crashing the system.

### 1b. Validate proposed prompts

- **Location:** `prompt_proposer.py`
- **Action:** After the LLM generates a new prompt, scan for `{...}` template variables.
- **Validation Rule:** Reject any prompt containing variables not in the allowed set: `borrower_name`, `account_last4`, `total_debt`, `debt_type`, `days_past_due`, `min_settlement_pct`, `max_settlement_pct`, `max_installments`.
- **Template Update:** Add an explicit list of **ALLOWED** variables to the `PROPOSE_PROMPT` template (line 42 currently says "preserve template variables" but lacks explicit definition).

---

## Fix 2: Improve Adoption Rate

**Target Files:** `statistical.py`, config/settings, `prompt_proposer.py`

### 2a. Relax initial statistical thresholds

- **Location:** `statistical.py` > `should_adopt()` (lines 120-155)
- **Action:** Change the adoption logic from "at least one metric significant" to composite-based.
- Compute net weighted improvement across all metrics.
- Require net positive effect `≥ min_effect_size` (lower this to `0.05`).
- Use overall p-value from a paired comparison of weighted composite scores.

- **Guardrail Adjustment:** Keep the regression guard but soften it. Only block adoption if any single metric drops by `> 0.3` (changed from `0.2`) with `p < 0.1`.

### 2b. Use two-sided test + practical significance

- **Location:** `statistical.py`
- **Action:** Keep the Wilcoxon test but add a composite score comparison path.
- **Implementation:** Add `compare_composite()` that takes all per-conversation weighted scores and runs a single paired test. This yields more statistical power than testing each metric individually.

### 2c. Start with more relaxed defaults

- **Location:** `config/settings`
- **Adjustments:**
- Default `stat_significance_p` = `0.15` (from `0.1`)
- Default `min_effect_size` = `0.05` (from `0.1`)

### 2d. Improve prompt proposer guidance

- **Location:** `prompt_proposer.py`
- **Action:** Add specific mutation guidance.
- Include examples of effective changes.
- Instruct the LLM to make **ONE** targeted change rather than rewriting the entire prompt.
- Include specific failure examples more prominently in the context.

---

## Fix 3: Reduce Hardship Bias

**Target Files:** `personas.py`, `simulator.py`, `evaluator.py`, `metrics.py`

### 3a. Rebalance personas

- **Location:** `personas.py`
- **Action:** Add 2 new personas to dilute hardship representation (changing the hardship distribution from 40% to ~29%):
- **Pragmatic Pat:** Has income, just prioritized other bills. Will negotiate a payment plan if terms are reasonable. _Not in hardship._
- **Skeptical Sam:** Thinks debt is settled/expired. Challenges legitimacy but will accept if shown proof. Not emotional. _Not in hardship._

### 3b. Make outcome classifier stricter

- **Location:** `simulator.py` > `_llm_check_outcome()`
- **Action:** Tighten the prompt to require an explicit borrower request for hardship.
- `hardship_requested` should only trigger when the borrower explicitly asks for or accepts enrollment in a hardship/relief program. (An agent merely mentioning hardship availability does not count).

- **Keyword Cleanup:** Remove overly broad fallback keywords like `"can't afford"`, `"payment pause"`, and `"forbearance"`.
- **New Outcome Category:** Add a 4th outcome called `hardship_offered` (for when the agent offered it, but the borrower didn't explicitly request or accept it).

### 3c. Update `make_test_borrower()`

- **Location:** `simulator.py`
- **Action:** Add `debt_map` entries for the 2 new personas.

### 3d. Add new evaluation metrics for resolution effectiveness

- **Location:** `evaluator.py`, `metrics.py`
- **Action:** Add an `outcome_quality` metric for the resolution agent.
- **Criteria:** "Did the agent push for a concrete financial commitment (payment plan or settlement) rather than defaulting to hardship referral?"
- **Weight:** `1.0` (This counterbalances the tendency to always route to hardship).

---

## Fix 4: Meta-Evaluator Improvements

**Target File:** `meta_evaluator.py`

### 4a. Add outcome distribution check

- **Action:** Create `_check_outcome_distribution()`. If `> 50%` of outcomes are `hardship_requested`, flag it as a problem.
- **Resolution:** Increase the weight of the `outcome_quality` metric and log a warning.

### 4b. Faster threshold adaptation

- **Action:** Change the threshold calibration trigger from `< 0.15` to `< 0.25` adoption rate.
- **Resolution:** Make relaxation more aggressive by multiplying `effect_size` by `0.5` (changed from `0.7`).

### 4c. Track per-persona outcome distribution

- **Action:** Record outcomes per persona across iterations to detect if certain personas always produce the identical outcome (which indicates the system is failing to learn).

---

## Verification Checklist

- [ ] Run `python -m src.learning.loop` — verify no KeyErrors occur.
- [ ] Check adoption rate after 4+ iterations — verify it is `> 20%`.
- [ ] Check outcome distribution — verify `hardship_requested` is `< 35%` of all outcomes.
- [ ] Verify the meta-evaluator successfully catches outcome distribution issues.
- [ ] Verify all existing test suites pass.
