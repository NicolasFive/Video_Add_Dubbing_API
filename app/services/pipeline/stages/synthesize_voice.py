from __future__ import annotations

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
        for i, sub in enumerate(ctx.subtitles):
            tts_path = ctx.work_dir / f"tts_{i}.wav"
            if sub.sentiment == Sentiment.NEGATIVE:
                emotion = "angry"
            elif sub.sentiment == Sentiment.POSITIVE:
                emotion = "happy"
            else:
                emotion = "neutral"

            if self._check_speech_text_is_blank(sub.text):
                sub.translated_tts_path = None
                continue

            self.tts.synthesize(
                text=sub.text,
                expect_duration_ms=sub.tts_expected_duration_ms,
                output_path=tts_path,
                voice_type=ctx.voice_type,
                emotion=emotion,
            )
            sub.translated_tts_path = tts_path

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
        context_texts = self.emotionor.exec([sub.text for sub in ctx.subtitles])
        self._save_log(ctx, log_name="emotion_analysis", log_data=[{"text": sub.text, "context_text": context_texts[i]} for i, sub in enumerate(ctx.subtitles)])
        # 2. 再合成语音，传入情绪文本作为上下文提示
        for i, sub in enumerate(ctx.subtitles):
            tts_path = ctx.work_dir / f"tts_{i}.wav"

            if self._check_speech_text_is_blank(sub.text):
                sub.translated_tts_path = None
                continue

            self.tts.synthesize(
                text=sub.text,
                expect_duration_ms=sub.tts_expected_duration_ms,
                output_path=tts_path,
                voice_type=ctx.voice_type,
                context_texts=[context_texts[i]] if context_texts[i] else None,
                section_id=ctx.task_id, # 传入上下文标识
            )
            sub.translated_tts_path = tts_path

    @staticmethod
    def _check_speech_text_is_blank(text: str) -> bool:
        # 判断文本是否只包含不可读文本（如标点）
        readable_content = re.sub(r"[^\w\s]", "", text)
        return len(readable_content.strip()) == 0
