from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.subtitle.burner import FFmpegBurner

from app.services.pipeline.base import BasePipelineStage


class FFmpegBurnSubtitlesStage(BasePipelineStage):
    def __init__(self):
        self.sub_burner = FFmpegBurner()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        video_with_dubbing = ctx.work_dir / "video_with_dubbing.mp4"
        srt_path = ctx.work_dir / "subtitles.srt"
        final_video_path = ctx.work_dir / "final_video.mp4"
        self.sub_burner.burn(
            video_with_dubbing,
            srt_path,
            final_video_path,
            ctx.input_video_width,
            ctx.input_video_height,
            ctx.subtitle_font_size,
        )
        ctx.final_video_path = final_video_path

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass    