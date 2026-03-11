"""Version-controlled prompt storage."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.context.token_budget import count_tokens
from src.models.evaluation import PromptVersion

PROMPTS_DIR = Path("prompts")


class PromptStore:
    def __init__(self, base_dir: Path = PROMPTS_DIR):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _agent_dir(self, agent_type: str) -> Path:
        d = self.base_dir / agent_type
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_active(self, agent_type: str) -> PromptVersion | None:
        versions = self.get_history(agent_type)
        for v in reversed(versions):
            if v.is_active:
                return v
        return versions[-1] if versions else None

    def get_history(self, agent_type: str) -> list[PromptVersion]:
        agent_dir = self._agent_dir(agent_type)
        versions = []
        for f in sorted(agent_dir.glob("v*.json")):
            try:
                data = json.loads(f.read_text())
                versions.append(PromptVersion(
                    id=data["id"],
                    agent_type=data["agent_type"],
                    version=data["version"],
                    content=data["content"],
                    token_count=data["token_count"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    evaluation_data=data.get("evaluation_data", {}),
                    is_active=data.get("is_active", False),
                    parent_version_id=data.get("parent_version_id"),
                ))
            except (json.JSONDecodeError, KeyError):
                continue
        return versions

    def save_version(
        self,
        agent_type: str,
        content: str,
        evaluation_data: dict | None = None,
        parent_version_id: str | None = None,
        is_active: bool = False,
    ) -> PromptVersion:
        versions = self.get_history(agent_type)
        version_num = len(versions) + 1
        version_id = str(uuid.uuid4())[:8]

        # If setting as active, deactivate all others
        if is_active:
            for v in versions:
                if v.is_active:
                    self._update_active(agent_type, v.version, False)

        pv = PromptVersion(
            id=version_id,
            agent_type=agent_type,
            version=version_num,
            content=content,
            token_count=count_tokens(content),
            evaluation_data=evaluation_data or {},
            is_active=is_active,
            parent_version_id=parent_version_id,
        )

        self._write(agent_type, pv)
        return pv

    def rollback(self, agent_type: str, version_id: str) -> bool:
        versions = self.get_history(agent_type)
        target = None
        for v in versions:
            if v.id == version_id:
                target = v
                break

        if not target:
            return False

        # Deactivate all, activate target
        for v in versions:
            self._update_active(agent_type, v.version, v.id == version_id)
        return True

    def _write(self, agent_type: str, pv: PromptVersion) -> None:
        agent_dir = self._agent_dir(agent_type)
        path = agent_dir / f"v{pv.version}.json"
        data = {
            "id": pv.id,
            "agent_type": pv.agent_type,
            "version": pv.version,
            "content": pv.content,
            "token_count": pv.token_count,
            "created_at": pv.created_at.isoformat(),
            "evaluation_data": pv.evaluation_data,
            "is_active": pv.is_active,
            "parent_version_id": pv.parent_version_id,
        }
        path.write_text(json.dumps(data, indent=2))

    def _update_active(self, agent_type: str, version_num: int, is_active: bool) -> None:
        agent_dir = self._agent_dir(agent_type)
        path = agent_dir / f"v{version_num}.json"
        if path.exists():
            data = json.loads(path.read_text())
            data["is_active"] = is_active
            path.write_text(json.dumps(data, indent=2))
