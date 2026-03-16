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
        self.replacer.replace(
            ctx.input_video_path, mixed_audio_path, video_with_dubbing
        )