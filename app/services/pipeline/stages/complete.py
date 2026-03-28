from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.subtitle.burner import FFmpegBurner

from app.services.pipeline.base import BasePipelineStage


class CompleteStage(BasePipelineStage):
    def __init__(self):
        pass

    def run(self, ctx: ProcessingContext) -> None:
        pass

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass    
    
    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass