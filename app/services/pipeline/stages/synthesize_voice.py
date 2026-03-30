from __future__ import annotations

from pathlib import Path
import re

from app.models.domain import ProcessingContext, Sentiment, SubtitleLine
from app.services.tts.volcano_tts import VolcanoTTSService
from app.services.tts.volcano_tts_v2 import VolcanoTTSService as VolcanoTTSServiceV2
from app.services.translation.llm_emotionor import LLMEmotionor

from app.services.pipeline.base import BasePipelineStage


class VolcengineSynthesizeVoiceStage(BasePipelineStage):
    def __init__(self):
        self.tts = VolcanoTTSService()
        self.speaker_voice_map = {}

    def run(self, ctx: ProcessingContext) -> None:
        tts_dir = Path(ctx.work_dir) / "tts"
        tts_dir.mkdir(exist_ok=True)
        for i, sub in enumerate(ctx.optimized_subtitles):
            tts_path = tts_dir / f"tts_{i}.wav"
            if self._check_speech_text_is_blank(sub.translated_text):
                sub.translated_tts_path = None
                continue
            self._request(ctx, sub, tts_path)
            sub.translated_tts_path = str(tts_path)

    def restore(self, ctx: ProcessingContext) -> bool:
        tts_dir = Path(ctx.work_dir) / "tts"
        for i, sub in enumerate(ctx.optimized_subtitles):
            tts_path = tts_dir / f"tts_{i}.wav"
            if self._check_speech_text_is_blank(sub.translated_text):
                sub.translated_tts_path = None
                continue
            if not tts_path.exists():
                self._request(ctx, sub, tts_path)
            sub.translated_tts_path = str(tts_path)
        return True

    def logfile_name(self) -> str:
        pass

    def save_log(self, ctx: ProcessingContext) -> None:
        pass

    def read_log(self, ctx: ProcessingContext) -> str:
        pass

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass

    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass

    @staticmethod
    def _check_speech_text_is_blank(text: str) -> bool:
        # 判断文本是否只包含不可读文本（如标点）
        readable_content = re.sub(r"[^\w\s]", "", text)
        return len(readable_content.strip()) == 0
    
    def _request(self, ctx: ProcessingContext, subtitle: SubtitleLine, tts_path: Path)-> None:
            emotion = (
                "angry"
                if subtitle.sentiment == Sentiment.NEGATIVE
                else "happy" if subtitle.sentiment == Sentiment.POSITIVE else "neutral"
            )
            if subtitle.speaker not in self.speaker_voice_map:
                idx = len(self.speaker_voice_map.keys())
                self.speaker_voice_map[subtitle.speaker] = (
                    ctx.voice_types[idx]
                    if idx < len(ctx.voice_types)
                    else ctx.voice_types[0]
                )
            self.tts.synthesize(
                text=subtitle.translated_text,
                expect_duration_ms=subtitle.tts_expected_duration_ms,
                output_path=tts_path,
                voice_type=self.speaker_voice_map[subtitle.speaker],
                emotion=emotion,
            )

class VolcengineV2SynthesizeVoiceStage(BasePipelineStage):
    def __init__(self):
        self.tts = VolcanoTTSServiceV2()
        self.speaker_voice_map = {}

    def run(self, ctx: ProcessingContext) -> None:
        tts_dir = Path(ctx.work_dir) / "tts"
        tts_dir.mkdir(exist_ok=True)
        for i, sub in enumerate(ctx.optimized_subtitles):
            tts_path = tts_dir / f"tts_{i}.wav"
            if self._check_speech_text_is_blank(sub.translated_text):
                sub.translated_tts_path = None
                continue
            self._request(ctx, sub, tts_path)
            sub.translated_tts_path = str(tts_path)

    def restore(self, ctx: ProcessingContext) -> bool:
        tts_dir = Path(ctx.work_dir) / "tts"
        for i, sub in enumerate(ctx.optimized_subtitles):
            tts_path = tts_dir / f"tts_{i}.wav"
            if self._check_speech_text_is_blank(sub.translated_text):
                sub.translated_tts_path = None
                continue
            if not tts_path.exists():
                self._request(ctx, sub, tts_path)
            sub.translated_tts_path = str(tts_path)
        return True

    def logfile_name(self) -> str:
        pass

    def save_log(self, ctx: ProcessingContext) -> None:
        pass

    def read_log(self, ctx: ProcessingContext) -> str:
        pass

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass

    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass

    def _request(self, ctx: ProcessingContext, subtitle: SubtitleLine, tts_path: Path)-> None:
        if subtitle.speaker not in self.speaker_voice_map:
            idx = len(self.speaker_voice_map.keys())
            self.speaker_voice_map[subtitle.speaker] = (
                ctx.voice_types[idx]
                if idx < len(ctx.voice_types)
                else ctx.voice_types[0]
            )
        self.tts.synthesize(
            text=subtitle.translated_text,
            expect_duration_ms=subtitle.tts_expected_duration_ms,
            output_path=tts_path,
            voice_type=self.speaker_voice_map[subtitle.speaker],
            context_texts=[subtitle.emotion_context] if subtitle.emotion_context else None,
            section_id=ctx.task_id,  # 传入上下文标识
        )

    @staticmethod
    def _check_speech_text_is_blank(text: str) -> bool:
        # 判断文本是否只包含不可读文本（如标点）
        readable_content = re.sub(r"[^\w\s]", "", text)
        return len(readable_content.strip()) == 0
