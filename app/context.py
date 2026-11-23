from pathlib import Path

from fastapi import HTTPException

from app.config import settings

SKIPPED_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
MAX_CONTEXT_BYTES = 2_000_000
MAX_FILE_BYTES = 200_000


def read_project_context(paths: list[str]) -> list[dict[str, str]]:
    root = settings.project_root.resolve()
    files: list[dict[str, str]] = []
    total = 0

    for raw_path in paths:
        path = (root / raw_path).resolve()
        if not path.is_relative_to(root):
            raise HTTPException(status_code=400, detail=f"Path outside project: {raw_path}")
        if not path.is_file():
            raise HTTPException(status_code=404, detail=f"File not found: {raw_path}")

        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail=f"File too large: {raw_path}")
        total += size
        if total > MAX_CONTEXT_BYTES:
            raise HTTPException(status_code=413, detail="Project context exceeds 2 MB")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=415, detail=f"File is not UTF-8: {raw_path}") from exc
        files.append({"path": raw_path, "content": content})

    return files


def discover_project_files() -> list[str]:
    root = settings.project_root.resolve()
    if not root.is_dir():
        return []

    found: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIPPED_DIRS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if path.stat().st_size <= MAX_FILE_BYTES:
            found.append(relative)
        if len(found) >= 500:
            break
    return sorted(found)
