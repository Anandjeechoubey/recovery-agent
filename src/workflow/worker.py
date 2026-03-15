import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from src.config import settings
from src.workflow.activities import (
    create_handoff,
    run_assessment,
    run_final_notice,
    run_resolution,
    send_email_summary,
)
from src.workflow.collections_workflow import CollectionsWorkflow


async def main() -> None:
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[CollectionsWorkflow],
        activities=[run_assessment, run_resolution, run_final_notice, create_handoff, send_email_summary],
    )

    print(f"Worker started on task queue: {settings.temporal_task_queue}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
