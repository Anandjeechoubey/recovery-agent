from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.dependencies import get_temporal_client
from src.db import repo
from src.workflow.activities import get_manager
from src.workflow.collections_workflow import CollectionsWorkflow

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/{borrower_id}")
async def send_message(borrower_id: str, req: ChatRequest):
    """Send a borrower message and signal the Temporal workflow."""
    client = await get_temporal_client()
    workflow_id = f"collections-{borrower_id}"

    try:
        handle = client.get_workflow_handle(workflow_id)

        # Signal the workflow with the borrower's message
        await handle.signal(CollectionsWorkflow.receive_message, req.message)

        # Also feed the message to the activity's conversation manager
        manager = get_manager(workflow_id)
        manager.receive_message(req.message)

        # Get current state
        state = await handle.query(CollectionsWorkflow.get_state)

        return {
            "status": "message_sent",
            "current_stage": state.get("current_stage"),
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {e}")


@router.get("/{borrower_id}/history")
async def get_history(borrower_id: str):
    """Get conversation history from the database, with live workflow state."""
    client = await get_temporal_client()
    workflow_id = f"collections-{borrower_id}"

    # Get persisted messages from DB
    db_messages = await repo.get_conversation_messages(workflow_id)

    # Also get live messages from manager (may have messages not yet in DB)
    manager = get_manager(workflow_id)
    live_messages = manager.messages

    # Use DB messages as the primary source; fall back to live if DB is empty
    messages = db_messages if db_messages else live_messages

    # Get workflow state from Temporal
    state = {}
    try:
        handle = client.get_workflow_handle(workflow_id)
        state = await handle.query(CollectionsWorkflow.get_state)
    except Exception:
        pass

    return {
        **state,
        "messages": messages,
    }


@router.get("/{borrower_id}/conversations")
async def get_conversations(borrower_id: str):
    """Get all conversations for a borrower, grouped by stage."""
    conversations = await repo.get_borrower_conversations(borrower_id)
    if not conversations:
        raise HTTPException(status_code=404, detail="No conversations found")
    return conversations
