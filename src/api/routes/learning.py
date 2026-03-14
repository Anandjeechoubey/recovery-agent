"""API endpoints for learning loop report data."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user

router = APIRouter(prefix="/learning", tags=["learning"], dependencies=[Depends(get_current_user)])

DATA_DIR = Path("data")


@router.get("/evolution")
async def get_evolution_report():
    """Return the full evolution report JSON."""
    path = DATA_DIR / "reports" / "evolution_report.json"
    if not path.exists():
        return {"error": "No evolution data found. Run the learning loop first."}
    with open(path) as f:
        return json.load(f)


@router.get("/iterations")
async def list_iterations():
    """Return a summary list of all iterations."""
    path = DATA_DIR / "reports" / "evolution_report.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    iterations = data.get("iterations", [])
    return [
        {
            "iteration": it["iteration"],
            "timestamp": it.get("timestamp", ""),
            "cost_this_iteration": it.get("cost_this_iteration", 0),
            "cost_cumulative": it.get("cost_cumulative", 0),
            "agents": {
                at: {
                    "action": ad.get("action", "N/A"),
                    "baseline_weighted_score": ad.get("baseline_weighted_score", ad.get("baseline_score", 0)),
                    "candidate_weighted_score": ad.get("candidate_weighted_score", ad.get("candidate_score", 0)),
                }
                for at, ad in it.get("agents", {}).items()
            },
            "meta_findings_count": len(it.get("meta_evaluation", {}).get("findings", [])),
            "errors": it.get("errors", []),
        }
        for it in iterations
    ]


@router.get("/iterations/{iteration_num}")
async def get_iteration(iteration_num: int):
    """Return full detail for a single iteration."""
    path = DATA_DIR / "evaluations" / f"iteration_{iteration_num}.json"
    if not path.exists():
        return {"error": f"Iteration {iteration_num} not found"}
    with open(path) as f:
        return json.load(f)


@router.get("/cost")
async def get_cost_report():
    """Return the cost breakdown report."""
    path = DATA_DIR / "reports" / "cost_report.json"
    if not path.exists():
        return {"error": "No cost data found"}
    with open(path) as f:
        return json.load(f)


@router.get("/config")
async def get_run_config():
    """Return the run configuration for reproducibility."""
    path = DATA_DIR / "reports" / "run_config.json"
    if not path.exists():
        return {"error": "No run config found"}
    with open(path) as f:
        return json.load(f)


@router.get("/prompts/{agent_type}/timeline")
async def get_prompt_timeline(agent_type: str):
    """Return the prompt version timeline for an agent."""
    path = DATA_DIR / "reports" / "evolution_report.json"
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data.get("prompt_version_timeline", {}).get(agent_type, [])
