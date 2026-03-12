"""Main learning loop orchestrator."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

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
from src.learning.statistical import ComparisonResult, should_adopt, wilcoxon_compare

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


async def run_learning_loop() -> None:
    """Run the full self-learning loop."""
    cost_tracker = CostTracker(budget_usd=settings.learning_budget_usd)
    prompt_store = PromptStore()
    meta_evaluator = MetaEvaluator(cost_tracker=cost_tracker)

    # Initialize prompt store with default prompts
    for agent_type, prompt in DEFAULT_PROMPTS.items():
        if not prompt_store.get_active(agent_type):
            prompt_store.save_version(agent_type, prompt, is_active=True)

    # Track all iteration data for the report
    all_iteration_data = []

    for iteration in range(1, settings.max_learning_iterations + 1):
        if cost_tracker.budget_exceeded:
            logger.warning(f"Budget exceeded at iteration {iteration}. Stopping.")
            break

        logger.info(f"\n{'='*60}")
        logger.info(f"ITERATION {iteration} | {cost_tracker.summary()}")
        logger.info(f"{'='*60}")

        iteration_data = {
            "iteration": iteration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": {},
        }

        # Get current active prompts
        current_prompts = {}
        for agent_type in AGENT_TYPES:
            version = prompt_store.get_active(agent_type)
            current_prompts[agent_type] = version.content if version else DEFAULT_PROMPTS[agent_type]

        # --- BASELINE EVALUATION ---
        logger.info("Running baseline simulations...")
        baseline_results = await _run_evaluation_batch(
            current_prompts, cost_tracker, seed_offset=iteration * 1000,
        )

        # --- PER-AGENT IMPROVEMENT ---
        for agent_type in AGENT_TYPES:
            if cost_tracker.budget_exceeded:
                break

            logger.info(f"\n[ITERATION {iteration}] Optimizing {agent_type}...")

            # Analyze baseline scores for this agent
            agent_evals = baseline_results["per_agent_evals"].get(agent_type, [])
            agent_metrics = aggregate_eval_results(agent_evals, agent_type)
            baseline_compliance = baseline_results["compliance_rates"].get(agent_type, 1.0)
            baseline_weighted = compute_weighted_score(agent_metrics, agent_type)

            # Find weakest metric
            if not agent_metrics:
                logger.info(f"  No metrics for {agent_type}, skipping")
                continue

            weakest = min(agent_metrics, key=lambda m: m.value)
            logger.info(f"[ITERATION {iteration}] Weakest metric: {weakest.name} = {weakest.value:.2f}")

            # Get failure examples with eval data for better analysis
            failures = _get_failure_examples(
                baseline_results["pipeline_results"], agent_evals, agent_type, weakest.name,
            )

            # Propose mutation
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
            logger.info(f"[ITERATION {iteration}] Proposed change: {description}")

            if new_prompt == current_prompts[agent_type]:
                logger.info(f"  No change proposed, skipping")
                iteration_data["agents"][agent_type] = {
                    "action": "no_change",
                    "baseline_score": baseline_weighted,
                }
                continue

            # Evaluate candidate
            candidate_prompts = dict(current_prompts)
            candidate_prompts[agent_type] = new_prompt

            candidate_results = await _run_evaluation_batch(
                candidate_prompts, cost_tracker,
                seed_offset=iteration * 1000 + 500,
                run_type=f"{agent_type}_improvement"
            )

            # Statistical comparison
            candidate_evals = candidate_results["per_agent_evals"].get(agent_type, [])
            candidate_metrics = aggregate_eval_results(candidate_evals, agent_type)
            candidate_compliance = candidate_results["compliance_rates"].get(agent_type, 1.0)
            candidate_weighted = compute_weighted_score(candidate_metrics, agent_type)

            comparisons = []
            for bm in agent_metrics:
                cm = next((m for m in candidate_metrics if m.name == bm.name), None)
                if cm and bm.per_conversation_scores and cm.per_conversation_scores:
                    # Ensure same length for paired comparison
                    min_len = min(len(bm.per_conversation_scores), len(cm.per_conversation_scores))
                    comp = wilcoxon_compare(
                        bm.per_conversation_scores[:min_len],
                        cm.per_conversation_scores[:min_len],
                        alpha=meta_evaluator.p_value_threshold,
                        min_effect=meta_evaluator.min_effect_size,
                        metric_name=bm.name,
                    )
                    comparisons.append(comp)

            adopt, reason = should_adopt(comparisons, baseline_compliance, candidate_compliance)
            logger.info(f"  Decision: {'ADOPT' if adopt else 'REJECT'} — {reason}")

            meta_evaluator.record_adoption(adopt)

            if adopt:
                # Save new version as active
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
                        }
                        for c in comparisons
                    ],
                    "reason": reason,
                    "change_description": description,
                }
                parent = prompt_store.get_active(agent_type)
                prompt_store.save_version(
                    agent_type, new_prompt,
                    evaluation_data=eval_data,
                    parent_version_id=parent.id if parent else None,
                    is_active=True,
                )
                current_prompts[agent_type] = new_prompt

            iteration_data["agents"][agent_type] = {
                "action": "adopted" if adopt else "rejected",
                "change_description": description,
                "baseline_score": baseline_weighted,
                "candidate_score": candidate_weighted,
                "comparisons": [
                    {
                        "metric": c.metric_name,
                        "effect": c.effect_size,
                        "p_value": c.p_value,
                        "significant": c.is_significant,
                    }
                    for c in comparisons
                ],
                "reason": reason,
                "compliance_baseline": baseline_compliance,
                "compliance_candidate": candidate_compliance,
            }

            # Record for meta-evaluator
            meta_evaluator.record_evaluation(
                baseline_results["per_agent_evals"].get(agent_type, [{}])[0]
                if baseline_results["per_agent_evals"].get(agent_type)
                else {}
            )

        # --- META-EVALUATION (every iteration for faster feedback) ---
        if True:
            logger.info("\nRunning meta-evaluation...")
            sample_convs = []
            for pr in baseline_results["pipeline_results"][:3]:
                sample_convs.extend(pr.conversations)

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
                    }
                    for f in meta_report.findings
                ],
            }

        iteration_data["cost"] = cost_tracker.total_cost_usd
        all_iteration_data.append(iteration_data)

        # Save iteration data
        _save_iteration_data(iteration, iteration_data)

    # Save final cost report
    cost_tracker.save()
    logger.info(f"\nLearning loop complete. {cost_tracker.summary()}")

    # Save full evolution data
    _save_evolution_data(all_iteration_data)


async def _run_evaluation_batch(
    prompts: dict[str, str],
    cost_tracker: CostTracker,
    seed_offset: int = 0,
    run_type: str = 'baseline',
) -> dict:
    """Run a batch of pipeline simulations and evaluate them.

    Optimized: simulations run concurrently (bounded by semaphore),
    then evaluations + compliance checks run concurrently per result.
    """
    # Semaphore limits concurrent API calls to avoid rate-limiting
    sim_semaphore = asyncio.Semaphore(5)
    eval_semaphore = asyncio.Semaphore(10)

    # --- Phase 1: Run all pipeline simulations concurrently ---
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

    # --- Phase 2: Evaluate + compliance-check all results concurrently ---
    async def _eval_one_pipeline(result: PipelineResult):
        async with eval_semaphore:
            eval_scores = await evaluate_pipeline(result.conversations, cost_tracker)

            compliance_tasks = [evaluate_compliance([conv]) for conv in result.conversations]
            compliance_results = await asyncio.gather(*compliance_tasks)

            return eval_scores, compliance_results

    logger.info(f"Evaluating {len(pipeline_results)} pipeline results concurrently...")
    eval_tasks = [_eval_one_pipeline(r) for r in pipeline_results]
    eval_results = await asyncio.gather(*eval_tasks)

    # --- Phase 3: Aggregate results ---
    per_agent_evals: dict[str, list[dict]] = {at: [] for at in AGENT_TYPES}
    per_agent_violations: dict[str, list[list[dict]]] = {at: [] for at in AGENT_TYPES}

    for result, (eval_scores, compliance_results) in zip(pipeline_results, eval_results):
        for conv, (_, violations) in zip(result.conversations, compliance_results):
            agent_type = conv.agent_type
            if agent_type in eval_scores:
                per_agent_evals[agent_type].append(eval_scores[agent_type])
            per_agent_violations[agent_type].extend(violations)

    # Compute compliance rates
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
    """Extract failure examples sorted by worst metric score, with evaluator reasoning."""
    # Pair each conversation with its eval score for the target metric
    scored_examples = []
    for i, pr in enumerate(pipeline_results):
        for conv in pr.conversations:
            if conv.agent_type == agent_type:
                # Get the eval score for this conversation if available
                score = 5.0  # default high (will sort to bottom)
                reasoning = ""
                if i < len(per_agent_evals):
                    eval_data = per_agent_evals[i]
                    metric_data = eval_data.get(metric_name, {})
                    if isinstance(metric_data, dict):
                        score = metric_data.get("score", 5.0)
                        reasoning = metric_data.get("reasoning", "")

                # Build a rich snippet
                last_msgs = conv.messages[-6:]
                snippet = " | ".join(f"{m.role}: {m.content[:100]}" for m in last_msgs)
                if reasoning:
                    snippet = f"[Score: {score}, Reason: {reasoning}] {snippet}"
                scored_examples.append((score, snippet))
                break

    # Sort by score ascending (worst first) and return top 5
    scored_examples.sort(key=lambda x: x[0])
    return [snippet for _, snippet in scored_examples[:5]]


def _save_iteration_data(iteration: int, data: dict) -> None:
    path = DATA_DIR / "evaluations"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / f"iteration_{iteration}.json", "w") as f:
        json.dump(data, f, indent=2, default=str)


def _save_evolution_data(all_data: list[dict]) -> None:
    path = DATA_DIR / "reports"
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "evolution_report.json", "w") as f:
        json.dump(all_data, f, indent=2, default=str)


async def main():
    await run_learning_loop()


if __name__ == "__main__":
    asyncio.run(main())
