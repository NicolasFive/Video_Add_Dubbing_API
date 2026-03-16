from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.subtitle.generator import SubtitleGenerator

from app.services.pipeline.base import BasePipelineStage


class RuleBasedGenerateSubtitlesStage(BasePipelineStage):
    def __init__(self):
        self.sub_gen = SubtitleGenerator()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        srt_path = ctx.work_dir / "subtitles.srt"
        self.sub_gen.generate_srt(
            ctx.subtitles,
            srt_path,
            ctx.input_video_width,
            ctx.subtitle_font_size,
        )
        ctx.final_subtitle_path = srt_path