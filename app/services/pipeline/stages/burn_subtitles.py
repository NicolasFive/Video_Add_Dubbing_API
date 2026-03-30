from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.subtitle.burner import FFmpegBurner
from pathlib import Path
from app.services.pipeline.base import BasePipelineStage


class FFmpegBurnSubtitlesStage(BasePipelineStage):
    def __init__(self):
        self.sub_burner = FFmpegBurner()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        video_with_dubbing = Path(ctx.work_dir) / "video_with_dubbing.mp4"
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        final_video_path = Path(ctx.work_dir) / "final_video.mp4"

        if not video_with_dubbing.exists():
            video_with_dubbing = ctx.input_video_path
            
        self.sub_burner.burn(
            str(video_with_dubbing),
            str(srt_path),
            str(final_video_path),
            ctx.input_video_width,
            ctx.input_video_height,
            ctx.subtitle_font_size,
        )
        ctx.final_video_path = str(final_video_path)

    def restore(self, ctx: ProcessingContext) -> bool:
        pass

    def logfile_name(self) -> str:
        pass
    
    def save_log(self, ctx: ProcessingContext) -> None:
        pass
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass    
    
    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass