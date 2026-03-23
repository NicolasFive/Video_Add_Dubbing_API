from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.audio.separator import DemucsService

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
        
    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass