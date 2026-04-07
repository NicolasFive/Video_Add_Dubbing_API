from __future__ import annotations

import json
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

    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        ctx.translations = [TranslateLine(**item) for item in log_data]
        return True
    
    def logfile_name(self) -> str:
        return "translations"
    
    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx: ProcessingContext) -> list[dict]:
        return [asdict(item) for item in ctx.translations]

    def set_data(self, ctx: ProcessingContext, data: list[dict]) -> None:
        ctx.translations = [TranslateLine(**item) for item in data]

    def self_check(self, ctx) -> list[SelfCheckItem]:
        # 1. 原文不为空时，译文不能为空
        # 2. 译文不能包含英文
        # 3. 译文不能包含敏感词

        check_results = []
        pattern = re.compile(r'[a-zA-Z]')
        sensitive_words = ["博士", "TA", "ta",".com",".org",".net","http"]  # 这里可以替换成实际的敏感词列表
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
                continue
            arr  = [word for word in sensitive_words if word in line.translated_text] 
            if len(arr) > 0:
                check_results.append(
                    SelfCheckItem(
                        index=i,
                        check_point="translated_text",
                        issue=f"译文包含敏感词： {', '.join(arr)}。",
                        warning_content=line.translated_text,
                        confirm_content=line.translated_text,
                    )
                )
                continue
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
                continue
        return check_results
            

    def check_confirm(self, ctx, data: list[SelfCheckItem]) -> None:
        for item in data:
            ctx.translations[item.index].translated_text = item.confirm_content
