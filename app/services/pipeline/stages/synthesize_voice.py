from __future__ import annotations

from pathlib import Path
import re

from app.models.domain import ProcessingContext, Sentiment
from app.services.tts.volcano_tts import VolcanoTTSService
from app.services.tts.volcano_tts_v2 import VolcanoTTSService as VolcanoTTSServiceV2
from app.services.translation.llm_emotionor import LLMEmotionor

from app.services.pipeline.base import BasePipelineStage


class VolcengineSynthesizeVoiceStage(BasePipelineStage):
    def __init__(self):
        self.tts = VolcanoTTSService()

    def run(self, ctx: ProcessingContext) -> None:
        speaker_voice_map = {}

        for i, sub in enumerate(ctx.optimized_subtitles):
            tts_path = Path(ctx.work_dir) / f"tts_{i}.wav"
            
            emotion = (
                "angry"
                if sub.sentiment == Sentiment.NEGATIVE
                else "happy" if sub.sentiment == Sentiment.POSITIVE else "neutral"
            )

            if self._check_speech_text_is_blank(sub.translated_text):
                sub.translated_tts_path = None
                continue

            if sub.speaker not in speaker_voice_map:
                idx = len(speaker_voice_map.keys())
                speaker_voice_map[sub.speaker] = (
                    ctx.voice_types[idx]
                    if idx < len(ctx.voice_types)
                    else ctx.voice_types[0]
                )

            self.tts.synthesize(
                text=sub.translated_text,
                expect_duration_ms=sub.tts_expected_duration_ms,
                output_path=tts_path,
                voice_type=speaker_voice_map[sub.speaker],
                emotion=emotion,
            )
            sub.translated_tts_path = str(tts_path)

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass

    @staticmethod
    def _check_speech_text_is_blank(text: str) -> bool:
        # 判断文本是否只包含不可读文本（如标点）
        readable_content = re.sub(r"[^\w\s]", "", text)
        return len(readable_content.strip()) == 0


class VolcengineV2SynthesizeVoiceStage(BasePipelineStage):
    def __init__(self):
        self.tts = VolcanoTTSServiceV2()
        self.emotionor = LLMEmotionor()

    def run(self, ctx: ProcessingContext) -> None:
        # 1. 先分析情绪，得到每条字幕的情绪文本
        context_texts = self.emotionor.exec([sub.translated_text for sub in ctx.optimized_subtitles])
        self._save_log(
            ctx,
            log_name="emotion_analysis",
            log_data=[
                {"text": sub.translated_text, "context_text": context_texts[i]}
                for i, sub in enumerate(ctx.optimized_subtitles)
            ],
        )
        # 2. 再合成语音，传入情绪文本作为上下文提示
        speaker_voice_map = {}
        for i, sub in enumerate(ctx.optimized_subtitles):
            tts_path = Path(ctx.work_dir) / f"tts_{i}.wav"

            if self._check_speech_text_is_blank(sub.translated_text):
                sub.translated_tts_path = None
                continue

            if sub.speaker not in speaker_voice_map:
                idx = len(speaker_voice_map.keys())
                speaker_voice_map[sub.speaker] = (
                    ctx.voice_types[idx]
                    if idx < len(ctx.voice_types)
                    else ctx.voice_types[0]
                )

            self.tts.synthesize(
                text=sub.translated_text,
                expect_duration_ms=sub.tts_expected_duration_ms,
                output_path=tts_path,
                voice_type=speaker_voice_map[sub.speaker],
                context_texts=[context_texts[i]] if context_texts[i] else None,
                section_id=ctx.task_id,  # 传入上下文标识
            )
            sub.translated_tts_path = str(tts_path)

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass

    @staticmethod
    def _check_speech_text_is_blank(text: str) -> bool:
        # 判断文本是否只包含不可读文本（如标点）
        readable_content = re.sub(r"[^\w\s]", "", text)
        return len(readable_content.strip()) == 0
