from __future__ import annotations
from app.models.domain import ProcessingContext, Sentiment
import json
from app.services.pipeline.base import BasePipelineStage
from app.services.translation.llm_emotionor import EmotionContext, LLMEmotionor


class EmotionAnalysisBySentimentStage(BasePipelineStage):
    def __init__(self):
        self.emotionor = LLMEmotionor()
        self.emotion_context = {}

    def run(self, ctx: ProcessingContext) -> None:
        subtitles = (
            ctx.optimized_subtitles if ctx.optimized_subtitles else ctx.subtitles
        )
        text = "\n".join([sub.translated_text for sub in subtitles])
        emotion_context = self.emotionor.exec(text)
        self._parse_emotion_context(ctx, emotion_context)
        self.emotion_context = emotion_context.model_dump()

    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        self.emotion_context = log_data
        emotion_context = EmotionContext(**log_data)
        self._parse_emotion_context(ctx, emotion_context)
        return True

    def logfile_name(self) -> str:
        return "emotion_analysis"

    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.emotion_context
        super()._save_log(ctx, log_name=log_name, log_data=log_data)

    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)

    def get_data(self, ctx: ProcessingContext) -> dict:
        log_data = self.read_log(ctx)
        emotion_context = json.loads(log_data)
        return emotion_context

    def set_data(self, ctx, data: dict):
        self.emotion_context = data

    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass

    def _parse_emotion_context(
        self, ctx: ProcessingContext, emotion_context: EmotionContext
    ) -> None:

        subtitles = (
            ctx.optimized_subtitles if ctx.optimized_subtitles else ctx.subtitles
        )
        for sub in subtitles:
            context_text = (
                emotion_context.positive
                if sub.sentiment == Sentiment.POSITIVE
                else (
                    emotion_context.negative
                    if sub.sentiment == Sentiment.NEGATIVE
                    else emotion_context.neutral
                )
            )
            sub.emotion_context = context_text
