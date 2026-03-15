import os
from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
    HTTPException,
)
from app.models.schemas import TaskResponse, TaskStatusEnum
from app.tasks.worker import run_dubbing_task
from app.utils.file_manager import FileManager
import uuid
from typing import Optional
from datetime import datetime
import logging
from app.utils.redis_oper import save_task_status

logger = logging.getLogger(__name__)
router = APIRouter()


# 校验参数
def validate_params(
    task_id: Optional[str], video: Optional[UploadFile], audio: Optional[UploadFile]
):
    # 判断是否为新建任务，新建任务必须上传文件或提供文件下载路径
    if task_id is None and video is None and audio is None:
        raise HTTPException(
            status_code=400,
            detail="新建任务必须提供 'video' 上传文件 或 'audio' 上传文件。",
        )


async def get_actual_file_path(
    task_id: Optional[str], file: Optional[UploadFile]
):
    actual_file_path = None
    # 情况1：上传了文件
    if file is not None:
        actual_file_path = await FileManager.save_upload_file_async(
            file, file.filename, task_id
        )
    return actual_file_path


@router.post("", response_model=TaskResponse)
async def submit_dubbing_task(
    video: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    voice_type: Optional[str] = Form(None),
    task_id: Optional[str] = Form(None),
    start_step: Optional[str] = Form(None),
    end_step: Optional[str] = Form(None),
):
    # 1. 校验参数
    validate_params(task_id=task_id, video=video, audio=audio)
    # 2. 生成 Task ID
    if not task_id:
        task_id = str(uuid.uuid4())
    # 3. 获取文件路径
    actual_video_path = await get_actual_file_path(
        task_id=task_id, file=video
    )
    actual_audio_path = await get_actual_file_path(
        task_id=task_id, file=audio
    )
    
    logger.info(f"Received task {task_id}")

    # 4. 初始化任务状态 (存入 Redis/DB)
    save_task_status(task_id, TaskStatusEnum.PENDING.value, 0, "Queueing...")

    # 5. 触发异步任务
    # 注意：Celery 任务需要序列化路径
    run_dubbing_task.delay(
        task_id=task_id,
        input_video_path_str=(
            None if actual_video_path is None else str(actual_video_path)
        ),
        input_audio_path_str=(
            None if actual_audio_path is None else str(actual_audio_path)
        ),
        voice_type=voice_type,
        start_step=start_step,
        end_step=end_step,
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatusEnum.PENDING,
        message="Task submitted successfully",
        created_at=datetime.now().isoformat(),
    )
