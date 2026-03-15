from typing import Optional

from celery import Celery
from app.core.config import settings
from app.models.schemas import TaskStatusEnum
from app.services.pipeline import DubbingPipeline
from app.models.domain import ProcessingContext
from app.utils.file_manager import FileManager
from pathlib import Path
from app.utils.redis_oper import save_task_status
from app.tasks.backend import celery_app
import pickle
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=0)
def run_dubbing_task(
    self,
    task_id: str,
    input_video_path_str: Optional[str],
    input_audio_path_str: Optional[str],
    voice_type: str,
    start_step: str = None,
    end_step: str = None,
):
    """异步执行配音任务"""
    input_video_path = None if input_video_path_str is None else Path(input_video_path_str)
    input_audio_path = None if input_audio_path_str is None else Path(input_audio_path_str)
    work_dir = FileManager.get_task_dir(task_id)    

    ctx = ProcessingContext(
        task_id=task_id,
        input_video_path=input_video_path,
        input_audio_path=input_audio_path,
        work_dir=work_dir,
        voice_type=voice_type,
    )

    # 如果指定了 start_step，尝试加载之前保存的上下文
    if start_step:
        context_file = work_dir / "context.pkl"
        if context_file.exists():
            with open(context_file, "rb") as f:
                ctx = pickle.load(f)
            # 更新可能变化的参数
            ctx.input_video_path = ctx.input_video_path if not input_video_path else input_video_path
            ctx.input_audio_path = ctx.input_audio_path if not input_audio_path else input_audio_path
            ctx.voice_type = ctx.voice_type if not voice_type else voice_type

    def update_progress(step, percent, error=None):
        # 更新 Redis 中的任务状态
        save_task_status(task_id, TaskStatusEnum.PROCESSING.value, percent, step, error)

    try:
        pipeline = DubbingPipeline(ctx)
        result_ctx = pipeline.run(update_progress_callback=update_progress, start_step=start_step, end_step=end_step)

        # 移动结果到永久存储目录
        # final_dest = Path(settings.STORAGE_ROOT) / settings.RESULT_DIR / task_id
        # shutil.move(result_ctx.final_video_path, final_dest)

        # 更新状态为 Success
        save_task_status(task_id, TaskStatusEnum.SUCCESS.value, 100, "Completed", None)
        return {"status": "success", "video_path": str(result_ctx.final_video_path)}

    except Exception as exc:
        # 更新状态为 Failed
        save_task_status(task_id, TaskStatusEnum.FAILED.value, 100, "Failed", str(exc))
        
        # 尝试获取失败的步骤，用于重试时从该步骤开始
        retry_start_step = start_step
        context_file = work_dir / "context.pkl"
        if context_file.exists():
            try:
                with open(context_file, "rb") as f:
                    saved_ctx = pickle.load(f)
                retry_start_step = saved_ctx.current_step
            except Exception:
                pass  # 如果加载失败，使用原start_step
        
        
        logger.info("Retrying task, attempt #%d", (self.request.retries+1))
        self.retry(countdown=60,kwargs={
            'task_id': task_id,
            'input_video_path_str': input_video_path_str,
            'input_audio_path_str': input_audio_path_str,
            'voice_type': voice_type,
            'start_step': retry_start_step,
            'end_step': end_step,
        })
