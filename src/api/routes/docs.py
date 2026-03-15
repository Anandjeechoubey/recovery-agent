"""API routes for serving knowledge-base documentation."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/docs", tags=["docs"])

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "knowledge"


@router.get("/files")
async def list_doc_files():
    """Return a list of available markdown files in the knowledge directory."""
    if not KNOWLEDGE_DIR.exists():
        return []
    files = sorted(KNOWLEDGE_DIR.glob("*.md"))
    return [
        {"slug": f.stem, "filename": f.name}
        for f in files
    ]


@router.get("/files/{slug}")
async def get_doc_file(slug: str):
    """Return the content of a specific markdown file."""
    file_path = KNOWLEDGE_DIR / f"{slug}.md"
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Document '{slug}' not found")
    # Prevent path traversal
    if not file_path.resolve().is_relative_to(KNOWLEDGE_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Access denied")
    content = file_path.read_text(encoding="utf-8")
    return {"slug": slug, "filename": file_path.name, "content": content}
