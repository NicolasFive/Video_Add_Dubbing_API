from __future__ import annotations

import logging

from app.models.domain import ProcessingContext
from app.services.audio.mixer import PydubMixAudio

from app.services.pipeline.base import BasePipelineStage

logger = logging.getLogger(__name__)


class PydubMixAudioStage(BasePipelineStage):
    def __init__(self):
        self.audio_mixer = PydubMixAudio()

    def run(self, ctx: ProcessingContext) -> None:
        mixed_audio_path = ctx.work_dir / "mixed_audio.wav"
        self.audio_mixer.init_voice(str(ctx.instrumentals_audio_path))
        for sub in ctx.optimized_subtitles:
            if sub.translated_tts_path:
                logger.info(
                    "Adding overlay: %s %s",
                    str(sub.start_ms),
                    str(sub.translated_tts_path),
                )
                self.audio_mixer.add_overlay(
                    str(sub.translated_tts_path),
                    start_time_ms=sub.start_ms,
                )
        self.audio_mixer.export(str(mixed_audio_path))

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass