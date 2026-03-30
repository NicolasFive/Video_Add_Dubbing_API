from __future__ import annotations
import json
from app.models.domain import ProcessingContext
from app.services.audio.separator import DemucsService
from pathlib import Path
from app.services.pipeline.base import BasePipelineStage


class DemucsSeparateVocalsStage(BasePipelineStage):
    def __init__(self):
        self.separator = DemucsService()

    def run(self, ctx: ProcessingContext) -> None:
        audio_path = (
            ctx.input_audio_path
            if ctx.input_audio_path
            else ctx.input_video_path
        )

        vocals_path, inst_path = self.separator.separate(audio_path, ctx.work_dir)
        ctx.vocals_audio_path = vocals_path
        ctx.instrumentals_audio_path = inst_path
      
    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        ctx.vocals_audio_path = log_data.get("vocals_audio_path")
        ctx.instrumentals_audio_path = log_data.get("instrumentals_audio_path")
        return True

    def logfile_name(self) -> str:
        return "separate_vocals"
    
    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
      
    def get_data(self, ctx):
        return {
            "vocals_audio_path": ctx.vocals_audio_path,
            "instrumentals_audio_path": ctx.instrumentals_audio_path,
        }

    def set_data(self, ctx, data):
        ctx.vocals_audio_path = data.get("vocals_audio_path", ctx.vocals_audio_path)
        ctx.instrumentals_audio_path = data.get("instrumentals_audio_path", ctx.instrumentals_audio_path)
    
    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass