from fastapi import APIRouter
from app.models.schemas import TaskResult, TaskStatusEnum
import app.utils.redis_oper as redis_oper

router = APIRouter()

@router.get("/{task_id}", response_model=TaskResult)
async def get_task_status(task_id: str):
    # 从 Redis/DB 查询状态
    status_data = redis_oper.get_task_status(task_id)
    if status_data is None:
        return TaskResult(
            task_id=task_id,
            status=TaskStatusEnum.UNKNOWN.value,
            progress=0,
            current_step="Unknown"
        )
    return TaskResult(
        task_id=task_id,
        status=status_data.get("status", TaskStatusEnum.UNKNOWN.value),
        progress=int(status_data.get("progress", 0)),
        current_step=status_data.get("current_step", "Unknown")
    )