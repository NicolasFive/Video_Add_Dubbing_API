from __future__ import annotations

import json

from app.models.domain import (
    DurationRating,
    ProcessingContext,
    SubtitleLine,
)
from app.services.timing.speed_ratio import SpeedRatioChecker
from app.services.tts.volcano_tts import get_volcengine_params

from app.services.pipeline.base import BasePipelineStage


class RuleBasedBuildSubtitlesDataStage(BasePipelineStage):
    def __init__(self):
        self.speed_ratio_checker = SpeedRatioChecker()

    def run(self, ctx: ProcessingContext) -> None:
        # 构建 SubtitleLine 对象列表
        raw_subtitles = []
        for i, translation in enumerate(ctx.translations):
            transcript = ctx.transcripts[i]
            sub = SubtitleLine(
                start_ms=transcript.start_ms,
                end_ms=transcript.end_ms,
                text=translation.translated_text,
                sentiment=transcript.sentiment,
            )
            self._evaluate_speed_ratio(sub)
            raw_subtitles.append(sub)

        self._save_subtitles_log(ctx, raw_subtitles, suffix="raw")

        # 按字幕时长评级尝试合并或扩展时间轴
        handled_subtitles = []
        prev_sub = None
        for sub in raw_subtitles:
            # 判断是否与前一条超长字幕首尾相连，是则合并文本和时长
            if prev_sub and prev_sub.tts_duration_rating == DurationRating.TOO_LONG:
                gap = sub.start_ms - prev_sub.end_ms
                if gap < 100:
                    prev_sub.end_ms = sub.end_ms
                    prev_sub.text = "\n".join([prev_sub.text, sub.text])
                    self._evaluate_speed_ratio(prev_sub)
                    continue

                # 不合并时，优先利用相邻间隙向后扩展时长
                need_gap = (
                    prev_sub.tts_eval_speed_ratio
                    * prev_sub.tts_expected_duration_ms
                    / prev_sub.tts_expected_speed_ratio
                ) - prev_sub.tts_expected_duration_ms
                need_gap = max(0, need_gap)
                prev_sub.end_ms += int(min(gap, need_gap))
                self._evaluate_speed_ratio(prev_sub)

            handled_subtitles.append(sub)
            prev_sub = sub

        if not handled_subtitles:
            ctx.subtitles = handled_subtitles
            self._save_subtitles_log(ctx, handled_subtitles, suffix="final")
            return

        # 处理尾部超长字幕，必要时向前借时长或继续合并
        last_sub = handled_subtitles[-1]
        while (
            last_sub
            and last_sub.tts_duration_rating == DurationRating.TOO_LONG
            and len(handled_subtitles) > 1
        ):
            last_prev_sub = handled_subtitles[-2]
            gap = last_sub.start_ms - last_prev_sub.end_ms
            if gap < 500:
                last_prev_sub.end_ms = last_sub.end_ms
                last_prev_sub.text = "\n".join([last_prev_sub.text, last_sub.text])
                handled_subtitles.pop()
                self._evaluate_speed_ratio(last_prev_sub)
                last_sub = last_prev_sub
            else:
                need_gap = (
                    last_sub.tts_eval_speed_ratio
                    * last_sub.tts_expected_duration_ms
                    / last_sub.tts_expected_speed_ratio
                ) - last_sub.tts_expected_duration_ms
                need_gap = max(0, need_gap)
                last_sub.start_ms -= int(min(gap, need_gap))
                self._evaluate_speed_ratio(last_sub)
                break

        ctx.subtitles = handled_subtitles
        self._save_subtitles_log(ctx, handled_subtitles, suffix="final")

    def _evaluate_speed_ratio(self, sub: SubtitleLine) -> None:
        # 计算 TTS 目标时长与语速评估结果
        duration_ms = sub.tts_expected_duration_ms
        translated_params = get_volcengine_params(sub.text, duration_ms / 1000)
        translated_speed_ratio = translated_params.speed_ratio
        duration_rating, target_ratio = self.speed_ratio_checker.check(
            translated_speed_ratio
        )
        sub.tts_duration_rating = duration_rating
        sub.tts_expected_speed_ratio = target_ratio
        sub.tts_eval_speed_ratio = translated_speed_ratio

    def _save_subtitles_log(self,ctx: ProcessingContext, subtitles: list[SubtitleLine], suffix: str = "") -> None:
        log_data = []
        for sub in subtitles:
            log_data.append(
                {
                    "start_ms": sub.start_ms,
                    "end_ms": sub.end_ms,
                    "sentiment": sub.sentiment.value if sub.sentiment else None,
                    "text": sub.text,
                    "tts_duration_rating": (
                        sub.tts_duration_rating.value
                        if sub.tts_duration_rating
                        else None
                    ),
                    "tts_eval_speed_ratio": sub.tts_eval_speed_ratio,
                    "tts_expected_speed_ratio": sub.tts_expected_speed_ratio,
                    "tts_expected_duration_ms": sub.tts_expected_duration_ms,
                }
            )
        self._save_log(ctx, log_name=f"subtitles{f'_{suffix}' if suffix else ''}", log_data=log_data)