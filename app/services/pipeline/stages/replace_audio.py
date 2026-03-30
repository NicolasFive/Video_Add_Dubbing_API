from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.audio.replacer import FFmpegAudioReplacer
from pathlib import Path
from app.services.pipeline.base import BasePipelineStage


class FFmpegReplaceAudioStage(BasePipelineStage):
    def __init__(self):
        self.replacer = FFmpegAudioReplacer()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        video_with_dubbing = Path(ctx.work_dir) / "video_with_dubbing.mp4"
        mixed_audio_path = Path(ctx.work_dir) / "mixed_audio.wav"

        if not mixed_audio_path.exists():
            mixed_audio_path = Path(ctx.input_audio_path) if ctx.input_audio_path else None

        if mixed_audio_path is None or not mixed_audio_path.exists():
            mixed_audio_path = Path(ctx.input_video_path) if ctx.input_video_path else None

        self.replacer.replace(
            ctx.input_video_path,
            str(mixed_audio_path),
            str(video_with_dubbing),
        )

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


class FFmpegOriginalSwapStage(BasePipelineStage):
    def __init__(self):
        self.replacer = FFmpegAudioReplacer()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.final_video_path is None:
            return

        output_path = Path(ctx.work_dir) / "final_video_original_swap.mp4"
        audio_path = (
            ctx.input_audio_path
            if ctx.input_audio_path is not None
            else ctx.input_video_path
        )
        self.replacer.replace(ctx.final_video_path, audio_path, str(output_path))

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
