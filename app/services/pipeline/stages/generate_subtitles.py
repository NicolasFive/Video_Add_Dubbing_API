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
            ctx.optimized_subtitles,
            srt_path,
            ctx.input_video_width,
            ctx.subtitle_font_size,
        )
        ctx.final_subtitle_path = srt_path

    def get_data(self, ctx) -> str:
        srt_path = ctx.work_dir / "subtitles.srt"
        if srt_path.exists():
            with open(srt_path, "r", encoding="utf-8") as f:
                return f.read()
        return "None"

    def set_data(self, ctx, data: str):
        srt_path = ctx.work_dir / "subtitles.srt"
        data = data.replace("\r", "")  # 将转义的换行符转换为实际的换行
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(data)
