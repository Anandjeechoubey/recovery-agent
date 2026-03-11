from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from src.config import settings
from src.workflow.activities import get_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/vapi")
async def vapi_webhook(request: Request):
    """Handle Vapi webhook events.

    Vapi sends events during the call lifecycle:
    - assistant-request: Vapi asks for assistant config
    - end-of-call-report: Call has ended, transcript available
    - status-update: Call status changes
    - transcript: Real-time transcript updates
    """
    body = await request.json()
    message = body.get("message", {})
    event_type = message.get("type", "")

    if event_type == "assistant-request":
        # Vapi is asking for assistant configuration
        # This is used in "server URL" mode where we provide the config dynamically
        metadata = message.get("call", {}).get("metadata", {})
        workflow_id = metadata.get("workflow_id", "")
        system_prompt = metadata.get("system_prompt", "")
        first_message = metadata.get("first_message", "")

        return {
            "assistant": {
                "model": {
                    "provider": "azure-openai",
                    "model": settings.azure_openai_deployment,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                    ],
                },
                "firstMessage": first_message,
                "recordingEnabled": True,
            }
        }

    elif event_type == "end-of-call-report":
        # Call has ended — extract transcript and feed to workflow
        call = message.get("call", {})
        metadata = call.get("metadata", {})
        workflow_id = metadata.get("workflow_id", "")
        transcript = message.get("transcript", "")

        logger.info(f"Call ended for workflow {workflow_id}")

        if workflow_id:
            # Signal the conversation manager that the call is done
            manager = get_manager(workflow_id)
            manager.receive_message(f"[CALL_ENDED] Transcript: {transcript}")

    elif event_type == "transcript":
        # Real-time transcript update during the call
        call = message.get("call", {})
        metadata = call.get("metadata", {})
        workflow_id = metadata.get("workflow_id", "")
        text = message.get("transcript", "")
        role = message.get("role", "")

        if workflow_id and role == "user" and text:
            manager = get_manager(workflow_id)
            manager.receive_message(text)

    return {"status": "ok"}
