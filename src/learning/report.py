"""Evolution report generator."""

from __future__ import annotations

import json
from pathlib import Path

DATA_DIR = Path("data")


def generate_report() -> str:
    """Generate a human-readable evolution report from the raw data."""
    reports_dir = DATA_DIR / "reports"
    evals_dir = DATA_DIR / "evaluations"

    # Load evolution data
    evolution_path = reports_dir / "evolution_report.json"
    if not evolution_path.exists():
        return "No evolution data found. Run the learning loop first."

    with open(evolution_path) as f:
        evolution_data = json.load(f)

    # Load cost report
    cost_path = reports_dir / "cost_report.json"
    cost_data = {}
    if cost_path.exists():
        with open(cost_path) as f:
            cost_data = json.load(f)

    lines = []
    lines.append("# Evolution Report")
    lines.append(f"\nTotal iterations: {len(evolution_data)}")
    lines.append(f"Total cost: ${cost_data.get('total_cost_usd', 0):.4f} / ${cost_data.get('budget_usd', 20):.2f}")
    lines.append("")

    for iteration_data in evolution_data:
        iteration = iteration_data["iteration"]
        lines.append(f"\n## Iteration {iteration}")
        lines.append(f"Cost so far: ${iteration_data.get('cost', 0):.4f}")

        for agent_type, agent_data in iteration_data.get("agents", {}).items():
            lines.append(f"\n### {agent_type}")
            lines.append(f"  Action: {agent_data.get('action', 'N/A')}")

            if "change_description" in agent_data:
                lines.append(f"  Change: {agent_data['change_description']}")

            baseline = agent_data.get("baseline_score", 0)
            candidate = agent_data.get("candidate_score", 0)
            lines.append(f"  Baseline score: {baseline:.3f}")
            if agent_data.get("action") != "no_change":
                lines.append(f"  Candidate score: {candidate:.3f}")

            lines.append(f"  Compliance (baseline): {agent_data.get('compliance_baseline', 'N/A')}")
            lines.append(f"  Compliance (candidate): {agent_data.get('compliance_candidate', 'N/A')}")

            comparisons = agent_data.get("comparisons", [])
            if comparisons:
                lines.append("  Statistical comparisons:")
                for comp in comparisons:
                    sig = "***" if comp.get("significant") else ""
                    lines.append(
                        f"    {comp['metric']}: effect={comp['effect']:.3f}, "
                        f"p={comp['p_value']:.4f} {sig}"
                    )

            lines.append(f"  Reason: {agent_data.get('reason', 'N/A')}")

        # Meta-evaluation
        meta = iteration_data.get("meta_evaluation", {})
        if meta.get("findings"):
            lines.append("\n### Meta-Evaluation Findings")
            for finding in meta["findings"]:
                lines.append(f"  [{finding['check_type']}] {finding['description']}")
                lines.append(f"    Action: {finding['action_taken']}")

    # Prompt version history
    lines.append("\n\n## Prompt Version History")
    prompts_dir = Path("prompts")
    for agent_type in ["assessment", "resolution", "final_notice"]:
        agent_dir = prompts_dir / agent_type
        if not agent_dir.exists():
            continue
        lines.append(f"\n### {agent_type}")
        for f in sorted(agent_dir.glob("v*.json")):
            try:
                data = json.loads(f.read_text())
                active = " [ACTIVE]" if data.get("is_active") else ""
                lines.append(f"  v{data['version']}: {data['token_count']} tokens{active}")
                eval_d = data.get("evaluation_data", {})
                if eval_d.get("change_description"):
                    lines.append(f"    Change: {eval_d['change_description']}")
            except (json.JSONDecodeError, KeyError):
                continue

    report = "\n".join(lines)

    # Save report
    reports_dir.mkdir(parents=True, exist_ok=True)
    with open(reports_dir / "evolution_report.md", "w") as f:
        f.write(report)

    print(report)
    return report


if __name__ == "__main__":
    generate_report()
