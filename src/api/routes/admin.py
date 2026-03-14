from fastapi import APIRouter, Depends

from src.api.dependencies import get_current_user
from src.learning.prompt_store import PromptStore

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_user)])

_store = PromptStore()


@router.get("/prompts/{agent_type}")
async def list_prompts(agent_type: str):
    versions = _store.get_history(agent_type)
    return [
        {
            "id": v.id,
            "version": v.version,
            "is_active": v.is_active,
            "token_count": v.token_count,
            "created_at": v.created_at.isoformat(),
            "content": v.content,
        }
        for v in versions
    ]


@router.get("/prompts/{agent_type}/active")
async def get_active_prompt(agent_type: str):
    version = _store.get_active(agent_type)
    if not version:
        return {"error": "No active prompt found"}
    return {
        "id": version.id,
        "version": version.version,
        "content": version.content,
        "token_count": version.token_count,
        "evaluation_data": version.evaluation_data,
    }


@router.post("/prompts/{agent_type}/rollback/{version_id}")
async def rollback_prompt(agent_type: str, version_id: str):
    success = _store.rollback(agent_type, version_id)
    if not success:
        return {"error": "Version not found"}
    return {"status": "rolled_back", "version_id": version_id}
