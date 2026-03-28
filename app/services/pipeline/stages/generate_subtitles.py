from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.subtitle.generator import SubtitleGenerator

from app.services.pipeline.base import BasePipelineStage
from pathlib import Path


class RuleBasedGenerateSubtitlesStage(BasePipelineStage):
    def __init__(self):
        self.sub_gen = SubtitleGenerator()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        subtitles = ctx.optimized_subtitles if ctx.optimized_subtitles else ctx.subtitles
        self.sub_gen.generate_srt(
            subtitles,
            str(srt_path),
            ctx.input_video_width,
            ctx.subtitle_font_size,
        )
        ctx.final_subtitle_path = str(srt_path)

    def get_data(self, ctx) -> str:
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        if srt_path.exists():
            with open(srt_path, "r", encoding="utf-8") as f:
                return f.read()
        return "None"

    def set_data(self, ctx, data: str):
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        data = data.replace("\r", "")  # 将转义的换行符转换为实际的换行
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(data)

    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass