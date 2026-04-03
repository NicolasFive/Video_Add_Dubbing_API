from typing import Optional

from celery import Celery
from app.core.config import settings
from app.models.schemas import TaskStatusEnum
from app.services.pipeline import DubbingPipeline
from app.models.domain import ProcessingContext
from app.utils.file_manager import FileManager
from app.utils.redis_oper import save_task_status
from app.tasks.backend import celery_app
from app.services.pipeline.registry import build_stage_configs
import pickle
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=0)
def run_dubbing_task(
    self,
    task_id: str,
    input_video_path: Optional[str],
    input_audio_path: Optional[str],
    voice_types: list[str],
    line_type: str = "default",
    start_step: str = None,
    end_step: str = None,
    duck_db: Optional[int] = None,
    no_cache: Optional[bool] = False,
):
    """异步执行配音任务"""
    work_dir = FileManager.get_task_dir(task_id)    

    ctx = ProcessingContext(
        task_id=task_id,
        input_video_path=input_video_path,
        input_audio_path=input_audio_path,
        work_dir=str(work_dir),
        voice_types=voice_types,
        line_type=line_type,
        duck_db=duck_db,
        no_cache=no_cache,
    )

    # 尝试加载之前保存的上下文
    context_file = work_dir / "context.pkl"
    if context_file.exists():
        with open(context_file, "rb") as f:
            ctx = pickle.load(f)
        # 更新可能变化的参数
        ctx.input_video_path = ctx.input_video_path if not input_video_path else input_video_path
        ctx.input_audio_path = ctx.input_audio_path if not input_audio_path else input_audio_path
        ctx.voice_types = ctx.voice_types if not voice_types else voice_types
        ctx.duck_db = ctx.duck_db if duck_db is None else duck_db
        ctx.no_cache = ctx.no_cache if no_cache is None else no_cache
        # line_type 从参数中获取，不覆盖已保存的
        if line_type == "default":
            line_type = ctx.line_type

    def update_progress(step, percent, error=None):
        # 更新 Redis 中的任务状态
        save_task_status(task_id, TaskStatusEnum.PROCESSING.value, percent, step, error)

    try:
        # 根据 line_type 获取对应的 stage_configs
        stage_configs = build_stage_configs(ctx.line_type)
        pipeline = DubbingPipeline(ctx, stage_configs=stage_configs)
        result_ctx = pipeline.run(update_progress_callback=update_progress, start_step=start_step, end_step=end_step)

        # 移动结果到永久存储目录
        # final_dest = Path(settings.STORAGE_ROOT) / settings.RESULT_DIR / task_id
        # shutil.move(result_ctx.final_video_path, final_dest)
        return {"status": "success"}

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
            'input_video_path': input_video_path,
            'input_audio_path': input_audio_path,
            'voice_types': voice_types,
            'start_step': retry_start_step,
            'end_step': end_step,
            'line_type': line_type,
        })
