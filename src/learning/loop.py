"""Main learning loop orchestrator."""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import numpy as np
from langfuse import get_client as get_langfuse_client
from langfuse import observe

from src.agents.assessment import ASSESSMENT_PROMPT, AssessmentAgent
from src.agents.final_notice import FINAL_NOTICE_PROMPT, FinalNoticeAgent
from src.agents.resolution import RESOLUTION_PROMPT, ResolutionAgent
from src.config import settings
from src.learning.compliance_eval import evaluate_compliance
from src.learning.cost_tracker import CostTracker
from src.learning.evaluator import evaluate_pipeline
from src.learning.meta_evaluator import MetaEvaluator
from src.learning.metrics import aggregate_eval_results, compute_weighted_score
from src.learning.personas import PERSONAS
from src.learning.prompt_proposer import propose_prompt_mutation
from src.learning.prompt_store import PromptStore
from src.learning.simulator import PipelineResult, simulate_pipeline
from src.learning.statistical import ComparisonResult, compare_composite, should_adopt, wilcoxon_compare

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

DATA_DIR = Path("data")
AGENT_TYPES = ["assessment", "resolution", "final_notice"]
DEFAULT_PROMPTS = {
    "assessment": ASSESSMENT_PROMPT,
    "resolution": RESOLUTION_PROMPT,
    "final_notice": FINAL_NOTICE_PROMPT,
}


def _get_run_config() -> dict:
    """Capture the full reproducibility config for this run."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "learning_budget_usd": settings.learning_budget_usd,
            "conversations_per_persona": settings.conversations_per_persona,
            "max_learning_iterations": settings.max_learning_iterations,
            "stat_significance_p": settings.stat_significance_p,
            "min_effect_size": settings.min_effect_size,
            "max_total_tokens": settings.max_total_tokens,
            "max_handoff_tokens": settings.max_handoff_tokens,
        },
        "personas": [p.name for p in PERSONAS],
        "num_personas": len(PERSONAS),
        "total_conversations_per_batch": len(PERSONAS) * settings.conversations_per_persona,
        "seed_formula": "seed = iteration * 1000 + persona_idx * 10 + repeat  (candidate: +500 offset)",
        "models": {
            "simulation_borrower": settings.azure_openai_deployment_mini,
            "simulation_agent": settings.azure_openai_deployment,
            "evaluation": settings.azure_openai_deployment_mini,
            "prompt_proposal": settings.azure_openai_deployment,
            "meta_evaluation": settings.azure_openai_deployment_mini,
        },
        "rerun_command": "python -m src.learning.loop",
    }


def _extract_per_conversation_detail(
    pipeline_results: list[PipelineResult],
    per_agent_evals: dict[str, list[dict]],
    compliance_rates: dict[str, float],
    run_label: str,
    iteration: int,
) -> list[dict]:
    """Extract per-conversation raw scores for CSV/JSON export."""
    rows = []
    agent_eval_idx = {at: 0 for at in AGENT_TYPES}

    for pr_idx, pr in enumerate(pipeline_results):
        persona_name = pr.conversations[0].borrower_id.replace("test-", "") if pr.conversations else "unknown"
        for conv in pr.conversations:
            at = conv.agent_type
            idx = agent_eval_idx[at]
            eval_data = {}
            if idx < len(per_agent_evals.get(at, [])):
                eval_data = per_agent_evals[at][idx]
            agent_eval_idx[at] = idx + 1

            row = {
                "iteration": iteration,
                "run_type": run_label,
                "pipeline_idx": pr_idx,
                "persona": persona_name,
                "agent_type": at,
                "outcome": conv.outcome or "",
                "num_messages": len(conv.messages),
            }
            for metric_name, metric_data in eval_data.items():
                if isinstance(metric_data, dict) and "score" in metric_data:
                    row[f"score_{metric_name}"] = metric_data["score"]
                    row[f"reasoning_{metric_name}"] = metric_data.get("reasoning", "")
            rows.append(row)
    return rows


def _build_metrics_detail(agent_metrics: list) -> dict:
    """Build detailed metrics dict with mean, std, min, max, n, per_conversation."""
    detail = {}
    for m in agent_metrics:
        scores = m.per_conversation_scores
        detail[m.name] = {
            "mean": round(m.value, 4),
            "std": round(float(np.std(scores)), 4) if scores else 0,
            "min": round(min(scores), 2) if scores else 0,
            "max": round(max(scores), 2) if scores else 0,
            "n": len(scores),
            "per_conversation": scores,
        }
    return detail


async def _improve_single_agent(
    agent_type: str,
    iteration: int,
    current_prompts: dict[str, str],
    baseline_results: dict,
    cost_tracker: CostTracker,
    meta_evaluator: MetaEvaluator,
    prompt_store: PromptStore,
    prompt_version_timeline: dict[str, list[dict]],
    all_raw_rows: list[dict],
) -> dict:
    """Run the improvement cycle for a single agent. Returns iteration agent data dict.

    Safe to run concurrently for different agent_types — each agent's candidate
    evaluation uses its own prompt copy and only writes to its own prompt namespace.
    """
    agent_evals = baseline_results["per_agent_evals"].get(agent_type, [])
    agent_metrics = aggregate_eval_results(agent_evals, agent_type)
    baseline_compliance = baseline_results["compliance_rates"].get(agent_type, 1.0)
    baseline_weighted = compute_weighted_score(agent_metrics, agent_type)
    baseline_metrics_detail = _build_metrics_detail(agent_metrics)

    if not agent_metrics:
        logger.info(f"  No metrics for {agent_type}, skipping")
        return {
            "action": "no_change",
            "baseline_weighted_score": baseline_weighted,
            "baseline_metrics": baseline_metrics_detail,
        }

    weakest = min(agent_metrics, key=lambda m: m.value)
    logger.info(f"[ITERATION {iteration}] {agent_type} weakest: {weakest.name} = {weakest.value:.2f}")

    failures = _get_failure_examples(
        baseline_results["pipeline_results"], agent_evals, agent_type, weakest.name,
    )

    score_summary = "\n".join(f"  {m.name}: {m.value:.2f}" for m in agent_metrics)
    description, new_prompt = await propose_prompt_mutation(
        agent_type=agent_type,
        current_prompt=current_prompts[agent_type],
        weakest_metric=weakest.name,
        weakest_score=weakest.value,
        failure_examples=failures,
        score_summary=score_summary,
        max_tokens=settings.max_total_tokens if agent_type == "assessment" else settings.max_total_tokens - settings.max_handoff_tokens,
        cost_tracker=cost_tracker,
    )
    logger.info(f"[ITERATION {iteration}] {agent_type} proposed: {description}")

    if new_prompt == current_prompts[agent_type]:
        logger.info(f"  {agent_type}: No change proposed, skipping")
        return {
            "action": "no_change",
            "baseline_weighted_score": baseline_weighted,
            "baseline_metrics": baseline_metrics_detail,
        }

    # Evaluate candidate — each agent gets its own prompt copy
    candidate_prompts = dict(current_prompts)
    candidate_prompts[agent_type] = new_prompt

    candidate_results = await _run_evaluation_batch(
        candidate_prompts, cost_tracker,
        seed_offset=iteration * 1000 + 500,
        run_type=f"{agent_type}_improvement"
    )

    candidate_rows = _extract_per_conversation_detail(
        candidate_results["pipeline_results"],
        candidate_results["per_agent_evals"],
        candidate_results["compliance_rates"],
        f"candidate_{agent_type}_iter{iteration}",
        iteration,
    )
    all_raw_rows.extend(candidate_rows)

    candidate_evals = candidate_results["per_agent_evals"].get(agent_type, [])
    candidate_metrics = aggregate_eval_results(candidate_evals, agent_type)
    candidate_compliance = candidate_results["compliance_rates"].get(agent_type, 1.0)
    candidate_weighted = compute_weighted_score(candidate_metrics, agent_type)
    candidate_metrics_detail = _build_metrics_detail(candidate_metrics)

    comparisons = []
    for bm in agent_metrics:
        cm = next((m for m in candidate_metrics if m.name == bm.name), None)
        if cm and bm.per_conversation_scores and cm.per_conversation_scores:
            min_len = min(len(bm.per_conversation_scores), len(cm.per_conversation_scores))
            comp = wilcoxon_compare(
                bm.per_conversation_scores[:min_len],
                cm.per_conversation_scores[:min_len],
                alpha=meta_evaluator.p_value_threshold,
                min_effect=meta_evaluator.min_effect_size,
                metric_name=bm.name,
            )
            comparisons.append(comp)

    # Compute composite score comparison for higher statistical power
    from src.learning.metrics import DEFAULT_METRIC_CONFIGS, MetricConfig
    metric_weights = {
        mc.name: mc.weight
        for mc in DEFAULT_METRIC_CONFIGS.get(agent_type, [])
        if mc.enabled
    }

    def _compute_per_conv_composite(evals: list[dict]) -> list[float]:
        composites = []
        for eval_data in evals:
            total_w, total_s = 0.0, 0.0
            for mname, mdata in eval_data.items():
                if isinstance(mdata, dict) and "score" in mdata:
                    w = metric_weights.get(mname, 1.0)
                    total_w += w
                    total_s += mdata["score"] * w
            if total_w > 0:
                composites.append(total_s / total_w)
        return composites

    baseline_composites = _compute_per_conv_composite(agent_evals)
    candidate_composites = _compute_per_conv_composite(candidate_evals)
    composite_result = None
    if baseline_composites and candidate_composites:
        min_len = min(len(baseline_composites), len(candidate_composites))
        composite_result = compare_composite(
            baseline_composites[:min_len],
            candidate_composites[:min_len],
            alpha=meta_evaluator.p_value_threshold,
            min_effect=meta_evaluator.min_effect_size,
        )

    adopt, reason = should_adopt(comparisons, baseline_compliance, candidate_compliance, composite_result)
    logger.info(f"  {agent_type}: {'ADOPT' if adopt else 'REJECT'} — {reason}")

    meta_evaluator.record_adoption(adopt)

    if adopt:
        eval_data = {
            "iteration": iteration,
            "baseline_score": baseline_weighted,
            "candidate_score": candidate_weighted,
            "comparisons": [
                {
                    "metric": c.metric_name,
                    "baseline_mean": c.baseline_mean,
                    "candidate_mean": c.candidate_mean,
                    "effect_size": c.effect_size,
                    "p_value": c.p_value,
                    "ci_lower": c.ci_lower,
                    "ci_upper": c.ci_upper,
                }
                for c in comparisons
            ],
            "reason": reason,
            "change_description": description,
        }
        parent = prompt_store.get_active(agent_type)
        new_version = prompt_store.save_version(
            agent_type, new_prompt,
            evaluation_data=eval_data,
            parent_version_id=parent.id if parent else None,
            is_active=True,
        )

        prompt_version_timeline[agent_type].append({
            "iteration": iteration,
            "version": new_version.version,
            "version_id": new_version.id,
            "token_count": new_version.token_count,
            "event": "adopted",
            "change_description": description,
            "baseline_weighted": baseline_weighted,
            "candidate_weighted": candidate_weighted,
        })

    meta_evaluator.record_evaluation(
        baseline_results["per_agent_evals"].get(agent_type, [{}])[0]
        if baseline_results["per_agent_evals"].get(agent_type)
        else {}
    )

    return {
        "action": "adopted" if adopt else "rejected",
        "change_description": description,
        "baseline_weighted_score": baseline_weighted,
        "candidate_weighted_score": candidate_weighted,
        "baseline_metrics": baseline_metrics_detail,
        "candidate_metrics": candidate_metrics_detail,
        "comparisons": [
            {
                "metric": c.metric_name,
                "baseline_mean": round(c.baseline_mean, 4),
                "candidate_mean": round(c.candidate_mean, 4),
                "effect_size": round(c.effect_size, 4),
                "p_value": round(c.p_value, 6),
                "ci_lower": round(c.ci_lower, 4),
                "ci_upper": round(c.ci_upper, 4),
                "significant": c.is_significant,
                "recommendation": c.recommendation,
            }
            for c in comparisons
        ],
        "reason": reason,
        "compliance_baseline": baseline_compliance,
        "compliance_candidate": candidate_compliance,
    }


@observe(name="learning_loop")
async def run_learning_loop() -> None:
    """Run the full self-learning loop."""
    cost_tracker = CostTracker(budget_usd=settings.learning_budget_usd)
    prompt_store = PromptStore()
    meta_evaluator = MetaEvaluator(cost_tracker=cost_tracker)

    run_config = _get_run_config()
    (DATA_DIR / "reports").mkdir(parents=True, exist_ok=True)
    with open(DATA_DIR / "reports" / "run_config.json", "w") as f:
        json.dump(run_config, f, indent=2)

    for agent_type, prompt in DEFAULT_PROMPTS.items():
        if not prompt_store.get_active(agent_type):
            prompt_store.save_version(agent_type, prompt, is_active=True)

    all_iteration_data = []
    all_raw_rows: list[dict] = []
    prompt_version_timeline: dict[str, list[dict]] = {at: [] for at in AGENT_TYPES}

    for agent_type in AGENT_TYPES:
        v = prompt_store.get_active(agent_type)
        if v:
            prompt_version_timeline[agent_type].append({
                "iteration": 0,
                "version": v.version,
                "version_id": v.id,
                "token_count": v.token_count,
                "event": "initial",
            })

    for iteration in range(1, settings.max_learning_iterations + 1):
        if cost_tracker.budget_exceeded:
            logger.warning(f"Budget exceeded at iteration {iteration}. Stopping.")
            break

        logger.info(f"\n{'='*60}")
        logger.info(f"ITERATION {iteration} | {cost_tracker.summary()}")
        logger.info(f"{'='*60}")

        cost_before_iteration = cost_tracker.total_cost_usd
        baseline_results = None

        iteration_data: dict = {
            "iteration": iteration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": {},
            "errors": [],
        }

        try:
            # Get current active prompts
            current_prompts = {}
            current_versions = {}
            for agent_type in AGENT_TYPES:
                version = prompt_store.get_active(agent_type)
                current_prompts[agent_type] = version.content if version else DEFAULT_PROMPTS[agent_type]
                current_versions[agent_type] = version.version if version else 1

            iteration_data["prompt_versions_at_start"] = dict(current_versions)

            # --- BASELINE EVALUATION ---
            logger.info("Running baseline simulations...")
            baseline_results = await _run_evaluation_batch(
                current_prompts, cost_tracker, seed_offset=iteration * 1000,
            )

            baseline_rows = _extract_per_conversation_detail(
                baseline_results["pipeline_results"],
                baseline_results["per_agent_evals"],
                baseline_results["compliance_rates"],
                f"baseline_iter{iteration}",
                iteration,
            )
            all_raw_rows.extend(baseline_rows)

            # Record outcomes for meta-evaluator's distribution analysis
            for pr in baseline_results["pipeline_results"]:
                persona_name = pr.conversations[0].borrower_id.replace("test-", "") if pr.conversations else ""
                meta_evaluator.record_outcome(pr.final_outcome, persona_name)

            iteration_data["baseline_per_conversation"] = {}
            for agent_type in AGENT_TYPES:
                agent_evals = baseline_results["per_agent_evals"].get(agent_type, [])
                per_conv_scores: dict[str, list[float]] = {}
                for eval_data in agent_evals:
                    for metric_name, metric_data in eval_data.items():
                        if isinstance(metric_data, dict) and "score" in metric_data:
                            per_conv_scores.setdefault(metric_name, []).append(metric_data["score"])
                iteration_data["baseline_per_conversation"][agent_type] = per_conv_scores

            # --- PER-AGENT IMPROVEMENT (parallelized) ---
            logger.info(f"\n[ITERATION {iteration}] Optimizing all 3 agents in parallel...")

            async def _safe_improve(at: str) -> tuple[str, dict]:
                try:
                    result = await _improve_single_agent(
                        agent_type=at,
                        iteration=iteration,
                        current_prompts=current_prompts,
                        baseline_results=baseline_results,
                        cost_tracker=cost_tracker,
                        meta_evaluator=meta_evaluator,
                        prompt_store=prompt_store,
                        prompt_version_timeline=prompt_version_timeline,
                        all_raw_rows=all_raw_rows,
                    )
                    return at, result
                except Exception as e:
                    err_msg = f"{at} improvement failed: {type(e).__name__}: {e}"
                    logger.error(err_msg)
                    logger.error(traceback.format_exc())
                    return at, {
                        "action": "error",
                        "error": err_msg,
                        "baseline_weighted_score": 0,
                        "baseline_metrics": {},
                    }

            agent_results = await asyncio.gather(*[_safe_improve(at) for at in AGENT_TYPES])

            for at, result in agent_results:
                iteration_data["agents"][at] = result
                if result.get("action") == "error":
                    iteration_data["errors"].append(result["error"])

        except Exception as e:
            err_msg = f"Iteration {iteration} baseline failed: {type(e).__name__}: {e}"
            logger.error(err_msg)
            logger.error(traceback.format_exc())
            iteration_data["errors"].append(err_msg)

        # --- META-EVALUATION ---
        try:
            logger.info("\nRunning meta-evaluation...")
            sample_convs = []
            if baseline_results and baseline_results.get("pipeline_results"):
                for pr in baseline_results["pipeline_results"][:3]:
                    sample_convs.extend(pr.conversations)

            if sample_convs:
                meta_report = await meta_evaluator.run_meta_evaluation(iteration, sample_convs)
                if meta_report.findings:
                    for finding in meta_report.findings:
                        logger.info(f"  META-EVAL: [{finding.check_type}] {finding.description}")
                        logger.info(f"    Action: {finding.action_taken}")
                iteration_data["meta_evaluation"] = {
                    "findings": [
                        {
                            "check_type": f.check_type,
                            "description": f.description,
                            "action_taken": f.action_taken,
                            "evidence": f.evidence,
                            "before": f.before,
                            "after": f.after,
                        }
                        for f in meta_report.findings
                    ],
                    "current_thresholds": {
                        "p_value_threshold": meta_evaluator.p_value_threshold,
                        "min_effect_size": meta_evaluator.min_effect_size,
                    },
                }
            else:
                iteration_data["meta_evaluation"] = {
                    "findings": [],
                    "current_thresholds": {
                        "p_value_threshold": meta_evaluator.p_value_threshold,
                        "min_effect_size": meta_evaluator.min_effect_size,
                    },
                }
        except Exception as e:
            err_msg = f"Meta-evaluation failed at iteration {iteration}: {type(e).__name__}: {e}"
            logger.error(err_msg)
            logger.error(traceback.format_exc())
            iteration_data["errors"].append(err_msg)
            iteration_data["meta_evaluation"] = {"findings": [], "error": err_msg}

        iteration_cost = cost_tracker.total_cost_usd - cost_before_iteration
        iteration_data["cost_cumulative"] = cost_tracker.total_cost_usd
        iteration_data["cost_this_iteration"] = round(iteration_cost, 4)
        all_iteration_data.append(iteration_data)

        _save_iteration_data(iteration, iteration_data)

        if iteration_data["errors"]:
            logger.warning(f"Iteration {iteration} had {len(iteration_data['errors'])} error(s), continuing...")

    # --- Finalize ---
    cost_tracker.save()
    logger.info(f"\nLearning loop complete. {cost_tracker.summary()}")

    _save_evolution_data(all_iteration_data, prompt_version_timeline, run_config, cost_tracker)
    _save_raw_csv(all_raw_rows)

    try:
        from src.learning.report import generate_report
        generate_report()
    except Exception as e:
        logger.error(f"Report generation failed: {e}")

    try:
        get_langfuse_client().flush()
    except Exception:
        pass


@observe()
async def _run_evaluation_batch(
    prompts: dict[str, str],
    cost_tracker: CostTracker,
    seed_offset: int = 0,
    run_type: str = 'baseline',
) -> dict:
    """Run a batch of pipeline simulations and evaluate them."""
    sim_semaphore = asyncio.Semaphore(15) if run_type == 'baseline' else asyncio.Semaphore(5)
    eval_semaphore = asyncio.Semaphore(15) if run_type == 'baseline' else asyncio.Semaphore(7)

    async def _run_one_sim(persona, persona_idx, repeat):
        async with sim_semaphore:
            if cost_tracker.budget_exceeded:
                return None
            seed = seed_offset + persona_idx * 10 + repeat
            logger.info(f"[ITERATION {int(seed_offset/1000)}], [RUN TYPE: {run_type}], Persona: {persona_idx}. {persona.name}, Repeat: {repeat}")
            return await simulate_pipeline(
                persona,
                assessment_prompt=prompts["assessment"],
                resolution_prompt=prompts["resolution"],
                final_notice_prompt=prompts["final_notice"],
                cost_tracker=cost_tracker,
                seed=seed,
            )

    sim_tasks = []
    for persona_idx, persona in enumerate(PERSONAS):
        for repeat in range(settings.conversations_per_persona):
            sim_tasks.append(_run_one_sim(persona, persona_idx, repeat))

    logger.info(f"Launching {len(sim_tasks)} pipeline simulations concurrently...")
    sim_results = await asyncio.gather(*sim_tasks)
    pipeline_results = [r for r in sim_results if r is not None]
    logger.info(f"Completed {len(pipeline_results)} simulations.")

    async def _eval_one_pipeline(result: PipelineResult):
        async with eval_semaphore:
            eval_scores = await evaluate_pipeline(result.conversations, cost_tracker)
            compliance_tasks = [evaluate_compliance([conv]) for conv in result.conversations]
            compliance_results = await asyncio.gather(*compliance_tasks)
            return eval_scores, compliance_results

    logger.info(f"Evaluating {len(pipeline_results)} pipeline results concurrently...")
    eval_tasks = [_eval_one_pipeline(r) for r in pipeline_results]
    eval_results = await asyncio.gather(*eval_tasks)

    per_agent_evals: dict[str, list[dict]] = {at: [] for at in AGENT_TYPES}
    per_agent_violations: dict[str, list[list[dict]]] = {at: [] for at in AGENT_TYPES}

    for result, (eval_scores, compliance_results) in zip(pipeline_results, eval_results):
        for conv, (_, violations) in zip(result.conversations, compliance_results):
            agent_type = conv.agent_type
            if agent_type in eval_scores:
                per_agent_evals[agent_type].append(eval_scores[agent_type])
            per_agent_violations[agent_type].extend(violations)

    compliance_rates = {}
    for agent_type in AGENT_TYPES:
        viols = per_agent_violations[agent_type]
        if viols:
            clean = sum(1 for v in viols if len(v) == 0)
            compliance_rates[agent_type] = clean / len(viols)
        else:
            compliance_rates[agent_type] = 1.0

    return {
        "pipeline_results": pipeline_results,
        "per_agent_evals": per_agent_evals,
        "compliance_rates": compliance_rates,
    }


def _get_failure_examples(
    pipeline_results: list[PipelineResult],
    per_agent_evals: list[dict],
    agent_type: str,
    metric_name: str,
) -> list[str]:
    """Extract failure examples sorted by worst metric score."""
    scored_examples = []
    for i, pr in enumerate(pipeline_results):
        for conv in pr.conversations:
            if conv.agent_type == agent_type:
                score = 5.0
                reasoning = ""
                if i < len(per_agent_evals):
                    eval_data = per_agent_evals[i]
                    metric_data = eval_data.get(metric_name, {})
                    if isinstance(metric_data, dict):
                        score = metric_data.get("score", 5.0)
                        reasoning = metric_data.get("reasoning", "")
                last_msgs = conv.messages[-6:]
                snippet = " | ".join(f"{m.role}: {m.content[:100]}" for m in last_msgs)
                if reasoning:
                    snippet = f"[Score: {score}, Reason: {reasoning}] {snippet}"
                scored_examples.append((score, snippet))
                break

    scored_examples.sort(key=lambda x: x[0])
    return [snippet for _, snippet in scored_examples[:5]]


def _save_iteration_data(iteration: int, data: dict) -> None:
    path = DATA_DIR / "evaluations"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / f"iteration_{iteration}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)


def _save_evolution_data(
    all_data: list[dict],
    prompt_timeline: dict[str, list[dict]],
    run_config: dict,
    cost_tracker: CostTracker,
) -> None:
    path = DATA_DIR / "reports"
    path.mkdir(parents=True, exist_ok=True)

    cost_by_category: dict[str, float] = {}
    for entry in cost_tracker.breakdown:
        op = entry["operation"]
        if op.startswith("sim_borrower"):
            cat = "simulation_borrower"
        elif op.startswith("sim_agent"):
            cat = "simulation_agent"
        elif op.startswith("eval_"):
            cat = "evaluation"
        elif op.startswith("propose_"):
            cat = "prompt_proposal"
        elif op.startswith("handoff"):
            cat = "handoff_summarization"
        elif op.startswith("meta_"):
            cat = "meta_evaluation"
        else:
            cat = "other"
        cost_by_category[cat] = cost_by_category.get(cat, 0) + entry["cost_usd"]

    evolution = {
        "run_config": run_config,
        "iterations": all_data,
        "prompt_version_timeline": prompt_timeline,
        "cost_summary": {
            "total_usd": round(cost_tracker.total_cost_usd, 4),
            "budget_usd": cost_tracker.budget_usd,
            "by_category": {k: round(v, 4) for k, v in sorted(cost_by_category.items())},
            "by_model": {
                "gpt-4o-mini": {
                    "input_tokens": cost_tracker.total_input_tokens,
                    "output_tokens": cost_tracker.total_output_tokens,
                },
                "gpt-4o": {
                    "input_tokens": cost_tracker.total_input_tokens_4o,
                    "output_tokens": cost_tracker.total_output_tokens_4o,
                },
            },
        },
    }

    with open(path / "evolution_report.json", "w") as f:
        json.dump(evolution, f, indent=2, default=str)


def _save_raw_csv(rows: list[dict]) -> None:
    """Save per-conversation raw scores as CSV."""
    if not rows:
        return
    path = DATA_DIR / "reports"
    path.mkdir(parents=True, exist_ok=True)

    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())

    fixed = ["iteration", "run_type", "pipeline_idx", "persona", "agent_type", "outcome", "num_messages"]
    score_cols = sorted(k for k in all_keys if k.startswith("score_"))
    reasoning_cols = sorted(k for k in all_keys if k.startswith("reasoning_"))
    other_cols = sorted(all_keys - set(fixed) - set(score_cols) - set(reasoning_cols))
    fieldnames = fixed + score_cols + reasoning_cols + other_cols

    with open(path / "per_conversation_scores.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    with open(path / "per_conversation_scores.json", "w") as f:
        json.dump(rows, f, indent=2, default=str)


async def main():
    await run_learning_loop()


if __name__ == "__main__":
    asyncio.run(main())
