from __future__ import annotations

import json

from app.models.domain import ProcessingContext, TranslateLine
from app.services.translation.llm_translator import LLMTranslator

from app.services.pipeline.base import BasePipelineStage


class OpenAITranslateStage(BasePipelineStage):
    def __init__(self):
        self.translator = LLMTranslator()

    def run(self, ctx: ProcessingContext) -> None:
        texts_to_translate = [line.text for line in ctx.transcripts]
        translated_texts = self.translator.exec(texts_to_translate)
        translations = []
        for i, transcript in enumerate(ctx.transcripts):
            translations.append(
                TranslateLine(
                    original_text=transcript.text,
                    translated_text=translated_texts[i],
                )
            )
        ctx.translations = translations
        self._save_log(ctx, log_name="translations", log_data=[{"original_text": item.original_text, "translated_text": item.translated_text} for item in translations])