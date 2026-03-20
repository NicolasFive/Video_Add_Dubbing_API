from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.core.config import settings
from app.models.schemas import TaskFileItem, TaskFilesResult, TaskStatusEnum
from app.utils.redis_oper import get_task_status

router = APIRouter()


def _resolve_task_dir(task_id: str) -> Path:
    task_dir = Path(settings.STORAGE_ROOT) / settings.TEMP_DIR / task_id
    if not task_dir.exists() or not task_dir.is_dir():
        raise HTTPException(status_code=404, detail="Task directory not found")
    return task_dir.resolve()


def _build_status(task_id: str) -> tuple[TaskStatusEnum, int, str, str | None]:
    status_data = get_task_status(task_id) or {}

    raw_status = str(status_data.get("status", TaskStatusEnum.UNKNOWN.value)).lower()
    try:
        status = TaskStatusEnum(raw_status)
    except ValueError:
        status = TaskStatusEnum.UNKNOWN

    progress = int(status_data.get("progress", 0))
    current_step = status_data.get("current_step", "Unknown")
    error_detail = status_data.get("error")
    return status, progress, current_step, error_detail


@router.get("/{task_id}", response_model=TaskFilesResult)
async def get_task_result_files(task_id: str):
    task_dir = _resolve_task_dir(task_id)

    files: list[TaskFileItem] = []
    for path in task_dir.rglob("*"):
        if not path.is_file():
            continue

        stat = path.stat()
        rel_path = path.relative_to(task_dir).as_posix()
        encoded_rel_path = quote(rel_path, safe="")
        files.append(
            TaskFileItem(
                file_name=path.name,
                relative_path=rel_path,
                size_bytes=stat.st_size,
                updated_at=datetime.fromtimestamp(stat.st_mtime),
                download_url=f"/v1/result/task_id/{task_id}/download?file={encoded_rel_path}",
            )
        )

    files.sort(key=lambda item: item.updated_at, reverse=True)

    status, progress, current_step, error_detail = _build_status(task_id)
    return TaskFilesResult(
        task_id=task_id,
        status=status,
        files=files,
        progress=progress,
        current_step=current_step,
        error_detail=error_detail,
    )


@router.get("/{task_id}/download")
async def download_task_file(task_id: str, file: str = Query(..., description="Task relative file path")):
    task_dir = _resolve_task_dir(task_id)

    if not file.strip():
        raise HTTPException(status_code=400, detail="file query cannot be empty")

    requested = (task_dir / file).resolve()
    try:
        requested.relative_to(task_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid file path") from exc

    if not requested.exists() or not requested.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=str(requested), filename=requested.name)
