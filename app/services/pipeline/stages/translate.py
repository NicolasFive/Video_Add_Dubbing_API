from __future__ import annotations


from app.models.domain import ProcessingContext, SelfCheckItem, TranslateLine
from app.services.translation.llm_translator import LLMTranslator
from dataclasses import asdict
import re
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
        self._save_translations_log(ctx)

    def get_data(self, ctx: ProcessingContext) -> list[dict]:
        return [asdict(item) for item in ctx.translations]

    def set_data(self, ctx: ProcessingContext, data: list[dict]) -> None:
        ctx.translations = [TranslateLine(**item) for item in data]
        self._save_translations_log(ctx)

    def self_check(self, ctx) -> list[SelfCheckItem]:
        # 1. 原文不为空时，译文不能为空
        # 2. 译文不能包含英文
        check_results = []
        pattern = re.compile(r'[a-zA-Z]')
        for i, line in enumerate(ctx.translations):
            if line.original_text.strip() and not line.translated_text.strip():
                check_results.append(
                    SelfCheckItem(
                        index=i,
                        check_point="translated_text",
                        issue=f"原文不为空，但译文为空，原文：{line.original_text}",
                        warning_content=line.original_text,
                        confirm_content="",
                    )
                )
            if re.search(pattern, line.translated_text):
                check_results.append(
                    SelfCheckItem(
                        index=i,
                        check_point="translated_text",
                        issue=f"译文包含英文。",
                        warning_content=line.translated_text,
                        confirm_content=line.translated_text,
                    )
                )
        return check_results
            

    def check_confirm(self, ctx, data: list[SelfCheckItem]) -> None:
        for item in data:
            ctx.translations[item.index].translated_text = item.confirm_content
        self._save_translations_log(ctx)

    def _save_translations_log(self, ctx: ProcessingContext) -> None:
        self._save_log(
            ctx,
            log_name="translations",
            log_data=[asdict(item) for item in ctx.translations],
        )
