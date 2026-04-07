from __future__ import annotations
from datetime import datetime
from app.models.domain import ProcessingContext
from app.services.pipeline.base import BasePipelineStage


class PrepareForBeginning(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        pass

    def restore(self, ctx: ProcessingContext) -> bool:
        pass

    def logfile_name(self) -> str:
        return "init"

    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)

    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)

    def get_data(self, ctx: ProcessingContext) -> dict:
        # 当前系统时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return {
            "task_id": ctx.task_id,
            "input_video_path": ctx.input_video_path,
            "input_audio_path": ctx.input_audio_path,
            "work_dir": ctx.work_dir,
            "voice_source": ctx.voice_source,
            "voice_types": ctx.voice_types,
            "line_type": ctx.line_type,
            "duck_db": ctx.duck_db,
            "no_cache": ctx.no_cache,
            "update_time": current_time,
        }

    def set_data(self, ctx: ProcessingContext, data: dict) -> None:
        pass

    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass
