"""Evolution report generator — produces a scientific-grade Markdown report."""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path("data")


def generate_report() -> str:
    """Generate a comprehensive evolution report from the raw data."""
    reports_dir = DATA_DIR / "reports"

    # Load evolution data
    evolution_path = reports_dir / "evolution_report.json"
    if not evolution_path.exists():
        return "No evolution data found. Run the learning loop first."

    with open(evolution_path) as f:
        evolution = json.load(f)

    run_config = evolution.get("run_config", {})
    iterations = evolution.get("iterations", [])
    prompt_timeline = evolution.get("prompt_version_timeline", {})
    cost_summary = evolution.get("cost_summary", {})

    lines: list[str] = []

    # ── Header ──
    lines.append("# Self-Learning Loop — Evolution Report")
    lines.append("")
    lines.append(f"**Generated:** {run_config.get('timestamp', 'N/A')}")
    lines.append(f"**Total iterations:** {len(iterations)}")
    lines.append(f"**Total cost:** ${cost_summary.get('total_usd', 0):.4f} / ${cost_summary.get('budget_usd', 20):.2f}")
    lines.append(f"**Rerun command:** `{run_config.get('rerun_command', 'python -m src.learning.loop')}`")
    lines.append("")

    # ── Reproducibility Config ──
    lines.append("## 1. Reproducibility Configuration")
    lines.append("")
    settings_cfg = run_config.get("settings", {})
    lines.append("| Parameter | Value |")
    lines.append("|---|---|")
    for k, v in settings_cfg.items():
        lines.append(f"| `{k}` | `{v}` |")
    lines.append(f"| personas | `{run_config.get('personas', [])}` |")
    lines.append(f"| conversations_per_batch | `{run_config.get('total_conversations_per_batch', 'N/A')}` |")
    lines.append(f"| seed_formula | `{run_config.get('seed_formula', 'N/A')}` |")
    lines.append("")
    models = run_config.get("models", {})
    if models:
        lines.append("**Models:**")
        for role, model in models.items():
            lines.append(f"- {role}: `{model}`")
        lines.append("")

    # ── Cost Breakdown ──
    lines.append("## 2. Cost Breakdown")
    lines.append("")
    lines.append(f"**Total spend:** ${cost_summary.get('total_usd', 0):.4f}")
    lines.append("")
    by_cat = cost_summary.get("by_category", {})
    if by_cat:
        lines.append("| Category | Cost (USD) | % of Total |")
        lines.append("|---|---|---|")
        total = cost_summary.get("total_usd", 1) or 1
        for cat, cost in sorted(by_cat.items(), key=lambda x: -x[1]):
            pct = cost / total * 100
            lines.append(f"| {cat} | ${cost:.4f} | {pct:.1f}% |")
        lines.append("")
    by_model = cost_summary.get("by_model", {})
    if by_model:
        lines.append("**Token usage by model:**")
        lines.append("")
        lines.append("| Model | Input Tokens | Output Tokens |")
        lines.append("|---|---|---|")
        for model, tokens in by_model.items():
            lines.append(f"| {model} | {tokens.get('input_tokens', 0):,} | {tokens.get('output_tokens', 0):,} |")
        lines.append("")

    # Per-iteration cost
    if iterations:
        lines.append("**Cost per iteration:**")
        lines.append("")
        lines.append("| Iteration | This Iteration | Cumulative |")
        lines.append("|---|---|---|")
        for it in iterations:
            lines.append(
                f"| {it['iteration']} | ${it.get('cost_this_iteration', 0):.4f} | ${it.get('cost_cumulative', 0):.4f} |"
            )
        lines.append("")

    # ── Per-Iteration Detail ──
    lines.append("## 3. Per-Iteration Evolution")
    lines.append("")

    for it_data in iterations:
        iteration = it_data["iteration"]
        lines.append(f"### Iteration {iteration}")
        lines.append("")
        lines.append(f"**Prompt versions at start:** {it_data.get('prompt_versions_at_start', {})}")
        lines.append("")

        for agent_type in ["assessment", "resolution", "final_notice"]:
            agent_data = it_data.get("agents", {}).get(agent_type)
            if not agent_data:
                continue

            action = agent_data.get("action", "N/A")
            action_badge = {"adopted": "ADOPTED", "rejected": "REJECTED", "no_change": "NO CHANGE"}.get(action, action.upper())

            lines.append(f"#### {agent_type} — **{action_badge}**")
            lines.append("")

            if "change_description" in agent_data:
                lines.append(f"> {agent_data['change_description']}")
                lines.append("")

            # Baseline metrics table with distributions
            baseline_metrics = agent_data.get("baseline_metrics", {})
            candidate_metrics = agent_data.get("candidate_metrics", {})

            if baseline_metrics:
                has_candidate = bool(candidate_metrics) and action != "no_change"

                if has_candidate:
                    lines.append("| Metric | Baseline Mean | Baseline Std | Candidate Mean | Candidate Std | Effect | p-value | Sig? |")
                    lines.append("|---|---|---|---|---|---|---|---|")
                else:
                    lines.append("| Metric | Mean | Std | Min | Max | N |")
                    lines.append("|---|---|---|---|---|---|")

                if has_candidate:
                    comparisons = {c["metric"]: c for c in agent_data.get("comparisons", [])}
                    for metric_name, bm in baseline_metrics.items():
                        cm = candidate_metrics.get(metric_name, {})
                        comp = comparisons.get(metric_name, {})
                        sig = "Yes ***" if comp.get("significant") else "No"
                        lines.append(
                            f"| {metric_name} | {bm.get('mean', 0):.3f} | {bm.get('std', 0):.3f} "
                            f"| {cm.get('mean', 0):.3f} | {cm.get('std', 0):.3f} "
                            f"| {comp.get('effect_size', 0):+.3f} | {comp.get('p_value', 1):.4f} | {sig} |"
                        )
                else:
                    for metric_name, bm in baseline_metrics.items():
                        lines.append(
                            f"| {metric_name} | {bm.get('mean', 0):.3f} | {bm.get('std', 0):.3f} "
                            f"| {bm.get('min', 0):.1f} | {bm.get('max', 0):.1f} | {bm.get('n', 0)} |"
                        )
                lines.append("")

            # Per-conversation raw scores
            if baseline_metrics and any("per_conversation" in v for v in baseline_metrics.values()):
                lines.append("<details><summary>Per-conversation raw scores (baseline)</summary>")
                lines.append("")
                lines.append("| Metric | Scores |")
                lines.append("|---|---|")
                for metric_name, bm in baseline_metrics.items():
                    scores = bm.get("per_conversation", [])
                    scores_str = ", ".join(f"{s:.1f}" for s in scores)
                    lines.append(f"| {metric_name} | [{scores_str}] |")
                lines.append("")
                lines.append("</details>")
                lines.append("")

            if candidate_metrics and action != "no_change":
                lines.append("<details><summary>Per-conversation raw scores (candidate)</summary>")
                lines.append("")
                lines.append("| Metric | Scores |")
                lines.append("|---|---|")
                for metric_name, cm in candidate_metrics.items():
                    scores = cm.get("per_conversation", [])
                    scores_str = ", ".join(f"{s:.1f}" for s in scores)
                    lines.append(f"| {metric_name} | [{scores_str}] |")
                lines.append("")
                lines.append("</details>")
                lines.append("")

            # Statistical comparison detail
            comparisons_list = agent_data.get("comparisons", [])
            if comparisons_list:
                lines.append("**Statistical tests:**")
                lines.append("")
                for comp in comparisons_list:
                    ci_str = ""
                    if "ci_lower" in comp and "ci_upper" in comp:
                        ci_str = f", 95% CI: [{comp['ci_lower']:+.3f}, {comp['ci_upper']:+.3f}]"
                    lines.append(
                        f"- **{comp['metric']}**: effect={comp.get('effect_size', 0):+.4f}, "
                        f"p={comp.get('p_value', 1):.6f}{ci_str} -> `{comp.get('recommendation', 'N/A')}`"
                    )
                lines.append("")

            # Weighted scores
            bw = agent_data.get("baseline_weighted_score", agent_data.get("baseline_score", 0))
            cw = agent_data.get("candidate_weighted_score", agent_data.get("candidate_score", 0))
            if action != "no_change":
                lines.append(f"**Weighted score:** baseline={bw:.3f}, candidate={cw:.3f} (delta={cw - bw:+.3f})")
            else:
                lines.append(f"**Weighted score:** baseline={bw:.3f}")
            lines.append("")

            # Compliance
            cb = agent_data.get("compliance_baseline")
            cc = agent_data.get("compliance_candidate")
            if cb is not None:
                if cc is not None and action != "no_change":
                    lines.append(f"**Compliance:** baseline={cb:.2%}, candidate={cc:.2%}")
                else:
                    lines.append(f"**Compliance:** baseline={cb:.2%}")
                lines.append("")

            lines.append(f"**Decision reason:** {agent_data.get('reason', 'N/A')}")
            lines.append("")

        # Meta-evaluation
        meta = it_data.get("meta_evaluation", {})
        if meta.get("findings"):
            lines.append("#### Meta-Evaluation Findings")
            lines.append("")
            for finding in meta["findings"]:
                lines.append(f"**[{finding['check_type']}]** {finding['description']}")
                lines.append(f"- Action: {finding['action_taken']}")
                if finding.get("evidence"):
                    lines.append(f"- Evidence: `{json.dumps(finding['evidence'], default=str)[:200]}`")
                if finding.get("before") or finding.get("after"):
                    lines.append(f"- Before: `{json.dumps(finding.get('before', {}), default=str)[:150]}`")
                    lines.append(f"- After: `{json.dumps(finding.get('after', {}), default=str)[:150]}`")
                lines.append("")

        thresholds = meta.get("current_thresholds", {})
        if thresholds:
            lines.append(f"**Active thresholds:** p={thresholds.get('p_value_threshold', 'N/A')}, min_effect={thresholds.get('min_effect_size', 'N/A')}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # ── Prompt Version History ──
    lines.append("## 4. Prompt Version History")
    lines.append("")
    prompts_dir = Path("prompts")
    for agent_type in ["assessment", "resolution", "final_notice"]:
        lines.append(f"### {agent_type}")
        lines.append("")
        timeline = prompt_timeline.get(agent_type, [])
        if timeline:
            lines.append("| Iteration | Version | Tokens | Event | Change |")
            lines.append("|---|---|---|---|---|")
            for entry in timeline:
                lines.append(
                    f"| {entry.get('iteration', 'N/A')} | v{entry.get('version', '?')} "
                    f"| {entry.get('token_count', '?')} | {entry.get('event', '')} "
                    f"| {entry.get('change_description', '—')[:80]} |"
                )
            lines.append("")

        # Also show from file system
        agent_dir = prompts_dir / agent_type
        if agent_dir.exists():
            lines.append("**All stored versions:**")
            lines.append("")
            for f in sorted(agent_dir.glob("v*.json")):
                try:
                    data = json.loads(f.read_text())
                    active = " **[ACTIVE]**" if data.get("is_active") else ""
                    eval_d = data.get("evaluation_data", {})
                    change = eval_d.get("change_description", "initial")
                    lines.append(f"- v{data['version']}: {data['token_count']} tokens{active} — {change[:100]}")
                except (json.JSONDecodeError, KeyError):
                    continue
            lines.append("")

    # ── Metrics Across Versions ──
    lines.append("## 5. Metrics Across Prompt Versions")
    lines.append("")
    lines.append("Tracking how each agent's metrics evolved across iterations:")
    lines.append("")

    for agent_type in ["assessment", "resolution", "final_notice"]:
        lines.append(f"### {agent_type}")
        lines.append("")

        # Collect baseline metrics across all iterations
        metric_names: set[str] = set()
        for it_data in iterations:
            bm = it_data.get("agents", {}).get(agent_type, {}).get("baseline_metrics", {})
            metric_names.update(bm.keys())

        if not metric_names:
            lines.append("_No data available._")
            lines.append("")
            continue

        sorted_metrics = sorted(metric_names)
        header = "| Iteration | " + " | ".join(f"{m} (mean +/- std)" for m in sorted_metrics) + " | Weighted |"
        separator = "|---|" + "|".join("---|" for _ in sorted_metrics) + "---|"
        lines.append(header)
        lines.append(separator)

        for it_data in iterations:
            it_num = it_data["iteration"]
            agent_data = it_data.get("agents", {}).get(agent_type, {})
            bm = agent_data.get("baseline_metrics", {})
            weighted = agent_data.get("baseline_weighted_score", agent_data.get("baseline_score", 0))
            cells = []
            for m in sorted_metrics:
                md = bm.get(m, {})
                if md:
                    cells.append(f"{md.get('mean', 0):.2f}+/-{md.get('std', 0):.2f}")
                else:
                    cells.append("—")
            lines.append(f"| {it_num} | " + " | ".join(cells) + f" | {weighted:.3f} |")
        lines.append("")

    # ── Meta-Evaluation Summary ──
    lines.append("## 6. Meta-Evaluation Summary (Darwin Godel Machine)")
    lines.append("")
    lines.append("The meta-evaluation layer monitors the learning process itself and adjusts")
    lines.append("evaluation methodology when it detects flaws.")
    lines.append("")

    all_findings = []
    for it_data in iterations:
        meta = it_data.get("meta_evaluation", {})
        for f in meta.get("findings", []):
            all_findings.append({"iteration": it_data["iteration"], **f})

    if all_findings:
        lines.append("| Iteration | Check Type | Description | Action Taken |")
        lines.append("|---|---|---|---|")
        for f in all_findings:
            lines.append(
                f"| {f['iteration']} | {f['check_type']} | {f['description'][:80]} | {f['action_taken'][:60]} |"
            )
        lines.append("")

        # Highlight the most impactful finding
        impactful = [f for f in all_findings if f["check_type"] in ("reliability", "correlation", "threshold")]
        if impactful:
            lines.append("### Key Meta-Evaluation Finding")
            lines.append("")
            best = impactful[0]
            lines.append(f"**Iteration {best['iteration']} — [{best['check_type']}]**")
            lines.append("")
            lines.append(f"{best['description']}")
            lines.append("")
            lines.append(f"**Action:** {best['action_taken']}")
            if best.get("before"):
                lines.append(f"- Before: `{json.dumps(best['before'], default=str)}`")
            if best.get("after"):
                lines.append(f"- After: `{json.dumps(best['after'], default=str)}`")
            lines.append("")
    else:
        lines.append("_No meta-evaluation findings recorded._")
        lines.append("")

    # ── Raw Data Files ──
    lines.append("## 7. Raw Data Files")
    lines.append("")
    lines.append("| File | Description |")
    lines.append("|---|---|")
    lines.append("| `data/reports/evolution_report.json` | Complete evolution data (all iterations, configs, cost) |")
    lines.append("| `data/reports/per_conversation_scores.csv` | Per-conversation raw metric scores |")
    lines.append("| `data/reports/per_conversation_scores.json` | Same as CSV but in JSON format |")
    lines.append("| `data/reports/cost_report.json` | Detailed cost breakdown by operation |")
    lines.append("| `data/reports/run_config.json` | Exact run configuration for reproducibility |")
    lines.append("| `data/evaluations/iteration_N.json` | Per-iteration detailed evaluation data |")
    lines.append("| `data/reports/meta_eval_iteration_N.json` | Meta-evaluation findings per iteration |")
    lines.append("")

    report = "\n".join(lines)

    # Save report
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "evolution_report.md", "w") as f:
        f.write(report)

    print(report)
    return report


if __name__ == "__main__":
    generate_report()
