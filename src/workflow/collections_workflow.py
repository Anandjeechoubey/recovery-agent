from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.workflow.activities import (
        create_handoff,
        run_assessment,
        run_final_notice,
        run_resolution,
    )


@dataclass
class WorkflowState:
    current_stage: str = "pending"
    assessment_result: dict | None = None
    resolution_result: dict | None = None
    final_notice_result: dict | None = None
    outcome: str = "pending"
    attempt: int = 0


@dataclass
class WorkflowResult:
    outcome: str  # "agreement", "resolved", "hardship_requested", "escalate", "no_response"
    stage_results: list[dict] = field(default_factory=list)


@workflow.defn
class CollectionsWorkflow:
    def __init__(self) -> None:
        self.state = WorkflowState()
        self._pending_messages: asyncio.Queue[str] = asyncio.Queue()
        self._response_queue: asyncio.Queue[str] = asyncio.Queue()
        self._conversation_history: list[dict] = []

    @workflow.run
    async def run(self, borrower_dict: dict) -> dict:
        workflow_id = workflow.info().workflow_id
        stage_results: list[dict] = []

        # Stage 1: Assessment (up to 3 attempts)
        self.state.current_stage = "assessment"
        assessment_result = None

        for attempt in range(3):
            self.state.attempt = attempt + 1
            assessment_result = await workflow.execute_activity(
                run_assessment,
                args=[borrower_dict, workflow_id],
                start_to_close_timeout=timedelta(minutes=30),
                heartbeat_timeout=timedelta(minutes=5),
            )
            if assessment_result["outcome"] != "no_response":
                break

        self.state.assessment_result = assessment_result
        stage_results.append(assessment_result)

        # Stage 2: Resolution (voice)
        self.state.current_stage = "resolution"
        handoff_1to2 = await workflow.execute_activity(
            create_handoff,
            args=[stage_results],
            start_to_close_timeout=timedelta(minutes=2),
        )

        resolution_result = await workflow.execute_activity(
            run_resolution,
            args=[borrower_dict, handoff_1to2, workflow_id],
            start_to_close_timeout=timedelta(minutes=30),
            heartbeat_timeout=timedelta(minutes=5),
        )
        self.state.resolution_result = resolution_result
        stage_results.append(resolution_result)

        if resolution_result["outcome"] == "deal_agreed":
            self.state.outcome = "agreement"
            self.state.current_stage = "complete"
            return WorkflowResult(
                outcome="agreement", stage_results=stage_results
            ).__dict__

        if resolution_result["outcome"] == "hardship_requested":
            self.state.outcome = "hardship_requested"
            self.state.current_stage = "complete"
            return WorkflowResult(
                outcome="hardship_requested", stage_results=stage_results
            ).__dict__

        # Stage 3: Final Notice
        self.state.current_stage = "final_notice"
        handoff_2to3 = await workflow.execute_activity(
            create_handoff,
            args=[stage_results],
            start_to_close_timeout=timedelta(minutes=2),
        )

        final_result = await workflow.execute_activity(
            run_final_notice,
            args=[borrower_dict, handoff_2to3, workflow_id],
            start_to_close_timeout=timedelta(hours=48),
            heartbeat_timeout=timedelta(minutes=10),
        )
        self.state.final_notice_result = final_result
        stage_results.append(final_result)

        if final_result["outcome"] == "resolved":
            self.state.outcome = "resolved"
        elif final_result["outcome"] == "hardship_requested":
            self.state.outcome = "hardship_requested"
        else:
            self.state.outcome = "escalate"

        self.state.current_stage = "complete"
        return WorkflowResult(
            outcome=self.state.outcome, stage_results=stage_results
        ).__dict__

    @workflow.signal
    async def receive_message(self, message: str) -> None:
        """Receive a chat message from the borrower."""
        self._pending_messages.put_nowait(message)

    @workflow.query
    def get_state(self) -> dict:
        return {
            "current_stage": self.state.current_stage,
            "outcome": self.state.outcome,
            "attempt": self.state.attempt,
        }
