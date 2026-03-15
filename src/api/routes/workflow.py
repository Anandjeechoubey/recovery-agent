from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_current_user, get_temporal_client
from src.config import settings
from src.db import repo
from src.models.borrower import Borrower, PolicyRanges
from src.workflow.collections_workflow import CollectionsWorkflow

router = APIRouter(prefix="/workflow", tags=["workflow"])


class StartWorkflowRequest(BaseModel):
    borrower_id: str
    name: str
    account_last4: str
    total_debt: float
    debt_type: str = "credit_card"
    days_past_due: int = 90
    phone_number: str = ""
    email: str = ""


@router.post("/start")
async def start_workflow(req: StartWorkflowRequest):
    client = await get_temporal_client()
    borrower = Borrower(
        id=req.borrower_id,
        name=req.name,
        account_last4=req.account_last4,
        total_debt=req.total_debt,
        debt_type=req.debt_type,
        days_past_due=req.days_past_due,
        phone_number=req.phone_number,
        email=req.email,
    )

    workflow_id = f"collections-{req.borrower_id}"
    handle = await client.start_workflow(
        CollectionsWorkflow.run,
        asdict(borrower),
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )

    # Persist borrower to database
    await repo.upsert_borrower(
        borrower_id=req.borrower_id,
        name=req.name,
        account_last4=req.account_last4,
        total_debt=req.total_debt,
        debt_type=req.debt_type,
        days_past_due=req.days_past_due,
        phone_number=req.phone_number,
        email=req.email,
        workflow_id=workflow_id,
    )

    return {"workflow_id": workflow_id, "run_id": handle.result_run_id}


@router.get("/{borrower_id}/status")
async def get_status(borrower_id: str):
    # Resolve actual workflow_id from DB (handles seeded borrowers)
    borrower_info = await repo.get_borrower(borrower_id)
    if borrower_info and borrower_info.get("workflow_id"):
        workflow_id = borrower_info["workflow_id"]
    else:
        workflow_id = f"collections-{borrower_id}"

    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id)
        state = await handle.query(CollectionsWorkflow.get_state)
        return state
    except Exception:
        # Fall back to DB-stored state (e.g. seeded borrowers with no live Temporal workflow)
        if borrower_info:
            return {
                "current_stage": borrower_info.get("current_stage") or "unknown",
                "outcome": borrower_info.get("outcome") or "unknown",
                "attempt": 0,
            }
        raise HTTPException(status_code=404, detail=f"Borrower '{borrower_id}' not found")


@router.get("/list")
async def list_workflows():
    """List all known borrower workflows with their current status."""
    client = await get_temporal_client()
    borrowers = await repo.list_borrowers()
    results = []

    for info in borrowers:
        workflow_id = info.get("workflow_id") or f"collections-{info['borrower_id']}"
        try:
            handle = client.get_workflow_handle(workflow_id)
            state = await handle.query(CollectionsWorkflow.get_state)
            results.append({**info, **state})
        except Exception:
            # Fall back to DB-stored stage/outcome (from seeded data)
            db_stage = info.get("current_stage") or "unknown"
            db_outcome = info.get("outcome") or "unknown"
            results.append({**info, "current_stage": db_stage, "outcome": db_outcome})

    return results


@router.post("/{borrower_id}/cancel")
async def cancel_workflow(borrower_id: str):
    client = await get_temporal_client()
    workflow_id = f"collections-{borrower_id}"
    try:
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
        return {"status": "cancelled"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{borrower_id}")
async def delete_borrower(borrower_id: str):
    """Delete a borrower and optionally cancel its Temporal workflow."""
    # Try to cancel the Temporal workflow (ignore errors if not running)
    try:
        client = await get_temporal_client()
        workflow_id = f"collections-{borrower_id}"
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
    except Exception:
        pass

    deleted = await repo.delete_borrower(borrower_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Borrower not found")
    return {"status": "deleted"}
