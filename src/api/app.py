from fastapi import FastAPI

from src.api.routes import admin, chat, workflow
from src.voice.webhook import router as vapi_router

app = FastAPI(
    title="Recovery Agents",
    description="Self-Learning AI Collections Agents",
    version="0.1.0",
)

app.include_router(workflow.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(vapi_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
