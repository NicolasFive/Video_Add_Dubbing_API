from __future__ import annotations

import logging

from app.models.domain import DurationRating, ProcessingContext, ReducerData
from app.services.translation.llm_reducer import LLMReducer

from app.services.pipeline.base import BasePipelineStage

logger = logging.getLogger(__name__)


class OpenAIReduceTextStage(BasePipelineStage):
    def __init__(self):
        self.reducer = LLMReducer()

    def run(self, ctx: ProcessingContext) -> None:
        reducer_data_list = []
        for sub in ctx.subtitles:
            if sub.tts_duration_rating == DurationRating.TOO_LONG:
                # 计算在目标速率下需要保留的字符长度
                proportion = sub.tts_expected_speed_ratio / sub.tts_eval_speed_ratio
                text_len = len(sub.text)
                expected_text_len = max(1, int(text_len * proportion))
                reducer_data_list.append(
                    ReducerData(text=sub.text, target_length=expected_text_len)
                )

        if not reducer_data_list:
            return

        reduced_texts = self.reducer.exec(reducer_data_list)
        reduced_index = 0
        for sub in ctx.subtitles:
            if sub.tts_duration_rating == DurationRating.TOO_LONG:
                reduced_text = reduced_texts[reduced_index]
                reducer_data_list[reduced_index].reduced_text = reduced_text
                expected_text_len = reducer_data_list[reduced_index].target_length
                if len(reduced_text) <= expected_text_len:
                    sub.tts_duration_rating = None
                    sub.text = reduced_text
                else:
                    logger.warning(
                        'Reduced text still too long. Expected max length: %s. BEFORE: "%s" AFTER: "%s"',
                        expected_text_len,
                        sub.text,
                        reduced_text,
                    )
                    sub.text = reduced_text
                reduced_index += 1
        self._save_log(ctx, log_name="reduced_texts", log_data=[{"text": rd.text, "target_length": rd.target_length, "reduced_text": rd.reduced_text} for rd in reducer_data_list])