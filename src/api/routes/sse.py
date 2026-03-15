from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from starlette.responses import StreamingResponse

from src.workflow.activities import get_manager

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/{borrower_id}/stream")
async def stream_messages(borrower_id: str):
    """SSE endpoint streaming chat messages and stage transitions."""
    workflow_id = f"collections-{borrower_id}"
    manager = get_manager(workflow_id)

    async def event_generator():
        cursor = 0
        heartbeat_interval = 15  # seconds

        # If manager already has an outcome (reconnecting to completed workflow),
        # flush remaining messages and send the outcome immediately.
        if manager.outcome != "pending":
            while cursor < len(manager.messages):
                msg = manager.messages[cursor]
                cursor += 1
                if msg["role"] == "system" and msg["content"].startswith("stage_change:"):
                    stage = msg["content"].split(":", 1)[1]
                    yield f"event: stage_change\ndata: {json.dumps({'stage': stage})}\n\n"
                elif msg["role"] == "system" and msg["content"].startswith("outcome:"):
                    pass  # will send below
                else:
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"
            yield f"event: outcome\ndata: {json.dumps({'outcome': manager.outcome})}\n\n"
            return

        while True:
            # Wait for new messages or timeout for heartbeat
            try:
                await asyncio.wait_for(
                    _wait_for_event(manager),
                    timeout=heartbeat_interval,
                )
            except asyncio.TimeoutError:
                # On heartbeat, check if manager got an outcome while we waited
                if manager.outcome != "pending":
                    # Flush remaining messages then send outcome
                    while cursor < len(manager.messages):
                        msg = manager.messages[cursor]
                        cursor += 1
                        if msg["role"] == "system":
                            continue
                        yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                    yield f"event: outcome\ndata: {json.dumps({'outcome': manager.outcome})}\n\n"
                    return
                yield f"event: heartbeat\ndata: {{}}\n\n"
                continue

            # Yield all new messages since cursor
            while cursor < len(manager.messages):
                msg = manager.messages[cursor]
                cursor += 1

                if msg["role"] == "system" and msg["content"].startswith("stage_change:"):
                    stage = msg["content"].split(":", 1)[1]
                    yield f"event: stage_change\ndata: {json.dumps({'stage': stage})}\n\n"
                elif msg["role"] == "system" and msg["content"].startswith("outcome:"):
                    outcome = msg["content"].split(":", 1)[1]
                    yield f"event: outcome\ndata: {json.dumps({'outcome': outcome})}\n\n"
                    return  # Close stream when workflow completes
                else:
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _wait_for_event(manager) -> None:
    """Wait for the new_message_event and clear it."""
    await manager.new_message_event.wait()
    manager.new_message_event.clear()
