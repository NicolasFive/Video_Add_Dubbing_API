from __future__ import annotations

from app.models.domain import ProcessingContext
from app.services.audio.replacer import FFmpegAudioReplacer

from app.services.pipeline.base import BasePipelineStage


class FFmpegReplaceAudioStage(BasePipelineStage):
    def __init__(self):
        self.replacer = FFmpegAudioReplacer()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        video_with_dubbing = ctx.work_dir / "video_with_dubbing.mp4"
        mixed_audio_path = ctx.work_dir / "mixed_audio.wav"
        
        if not mixed_audio_path.exists():
            mixed_audio_path = ctx.input_audio_path

        self.replacer.replace(
            ctx.input_video_path, mixed_audio_path, video_with_dubbing
        )
        
    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass





class FFmpegOriginalSwapStage(BasePipelineStage):
    def __init__(self):
        self.replacer = FFmpegAudioReplacer()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.final_video_path is None:
            return
        output_path = ctx.work_dir / "final_video_original_swap.mp4"
        audio_path = ctx.input_audio_path if ctx.input_audio_path is not None else ctx.input_video_path
        self.replacer.replace(
            ctx.final_video_path, audio_path, output_path
        )
        
    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass