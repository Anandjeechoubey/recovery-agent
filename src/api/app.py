from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from temporalio.client import Client
from temporalio.worker import Worker

from src.api.routes import admin, chat, docs, learning, workflow
from src.api.routes import auth as auth_route
from src.api.routes import sse as sse_route
from src.config import settings
from src.voice.webhook import router as vapi_router
from src.workflow.activities import (
    create_handoff,
    run_assessment,
    run_final_notice,
    run_resolution,
)
from src.workflow.collections_workflow import CollectionsWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


async def _run_worker() -> None:
    """Run the Temporal worker in the same process as the API."""
    try:
        client = await Client.connect(
            settings.temporal_host, namespace=settings.temporal_namespace
        )
        worker = Worker(
            client,
            task_queue=settings.temporal_task_queue,
            workflows=[CollectionsWorkflow],
            activities=[run_assessment, run_resolution, run_final_notice, create_handoff],
        )
        print(f"[WORKER] Embedded worker started on queue: {settings.temporal_task_queue}", flush=True)
        await worker.run()
    except Exception as e:
        print(f"[WORKER] Temporal worker FAILED: {e}", flush=True)
        import traceback
        traceback.print_exc()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    from src.db.session import init_db, close_db
    await init_db()
    logger.info("Database tables initialized")

    # Start Temporal worker as background task
    worker_task = asyncio.create_task(_run_worker())
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    await close_db()


app = FastAPI(
    title="Recovery Agents",
    description="Self-Learning AI Collections Agents",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes under /api prefix
app.include_router(auth_route.router, prefix="/api")
app.include_router(workflow.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(sse_route.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(learning.router, prefix="/api")
app.include_router(docs.router, prefix="/api")
app.include_router(vapi_router, prefix="/api")
app.include_router(vapi_router)  # Also register at root for Vapi webhook callbacks


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Serve frontend static files if the build exists
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for all non-API routes."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")
