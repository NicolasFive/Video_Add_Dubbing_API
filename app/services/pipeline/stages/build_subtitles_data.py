from __future__ import annotations

from dataclasses import asdict
import json
from app.models.domain import (
    DurationRating,
    ProcessingContext,
    SelfCheckItem,
    SubtitleLine,
)
from app.services.pipeline.base import BasePipelineStage
from app.services.timing.speed_ratio import SpeedRatioChecker
from app.services.tts.volcano_tts import get_volcengine_params


def evaluate_speed_ratio(sub: SubtitleLine) -> None:
    speed_ratio_checker = SpeedRatioChecker()
    duration_ms = sub.tts_expected_duration_ms
    translated_params = get_volcengine_params(sub.translated_text, duration_ms / 1000)
    translated_speed_ratio = translated_params.speed_ratio
    duration_rating, target_ratio = speed_ratio_checker.check(translated_speed_ratio)
    sub.tts_duration_rating = duration_rating
    sub.tts_expected_speed_ratio = target_ratio
    sub.tts_eval_speed_ratio = translated_speed_ratio


class BuildSubtitlesStage(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        subtitles = []
        for i, translation in enumerate(ctx.translations):
            transcript = ctx.transcripts[i]
            sub = SubtitleLine(
                start_ms=transcript.start_ms,
                end_ms=transcript.end_ms,
                original_text=(
                    transcript.text.replace("\n", " ") if transcript.text else ""
                ),
                translated_text=(
                    translation.translated_text.replace("\n", " ")
                    if translation.translated_text
                    else ""
                ),
                sentiment=transcript.sentiment,
                speaker=transcript.speaker,
            )
            evaluate_speed_ratio(sub)
            subtitles.append(sub)
        ctx.subtitles = subtitles

    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        ctx.subtitles = [SubtitleLine(**item) for item in log_data]
        return True

    def logfile_name(self) -> str:
        return "subtitles"
    
    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)

    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx: ProcessingContext) -> list[dict]:
        return [asdict(item) for item in ctx.subtitles]

    def set_data(self, ctx: ProcessingContext, data: list[dict]) -> None:
        ctx.subtitles = [SubtitleLine(**item) for item in data]

    def self_check(self, ctx):
        # 检查是否有优化后的字幕仍然过长
        check_results = []
        for i, sub in enumerate(ctx.subtitles):
            if sub.tts_duration_rating == DurationRating.TOO_LONG:
                check_results.append(
                    SelfCheckItem(
                        index=i,
                        check_point="tts_duration_rating",
                        issue=f"优化后的字幕仍然过长（{sub.tts_eval_speed_ratio}），原文：{sub.original_text}",
                        warning_content=sub.translated_text,
                        confirm_content=sub.translated_text,
                    )
                )

        return check_results

    def check_confirm(self, ctx, data):
        for item in data:
            ctx.subtitles[item.index].translated_text = item.confirm_content



class OptimizeSubtitlesStage(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        optimized_subtitles = []
        prev_sub = None
        for sub in ctx.subtitles:
            # 克隆一份，避免修改原始字幕数据
            sub = SubtitleLine(**asdict(sub))
            if (
                prev_sub
                and prev_sub.tts_duration_rating == DurationRating.TOO_LONG
                and sub.speaker == prev_sub.speaker
            ):
                gap = sub.start_ms - prev_sub.end_ms
                if gap < 1000:
                    prev_sub.end_ms = sub.end_ms
                    prev_sub.original_text = "\n".join(
                        [prev_sub.original_text, sub.original_text]
                    )
                    prev_sub.translated_text = "\n".join(
                        [prev_sub.translated_text, sub.translated_text]
                    )
                    evaluate_speed_ratio(prev_sub)
                    continue

                need_gap = (
                    prev_sub.tts_eval_speed_ratio
                    * prev_sub.tts_expected_duration_ms
                    / prev_sub.tts_expected_speed_ratio
                ) - prev_sub.tts_expected_duration_ms
                need_gap = max(0, need_gap)
                prev_sub.end_ms += int(min(gap, need_gap))
                evaluate_speed_ratio(prev_sub)

            optimized_subtitles.append(sub)
            prev_sub = sub

        if not optimized_subtitles:
            ctx.optimized_subtitles = optimized_subtitles
            return

        last_sub = optimized_subtitles[-1]
        while (
            last_sub
            and last_sub.tts_duration_rating == DurationRating.TOO_LONG
            and len(optimized_subtitles) > 1
        ):
            last_prev_sub = optimized_subtitles[-2]
            if last_prev_sub.speaker != last_sub.speaker:
                break
            gap = last_sub.start_ms - last_prev_sub.end_ms
            if gap < 500:
                last_prev_sub.end_ms = last_sub.end_ms
                last_prev_sub.original_text = "\n".join(
                    [last_prev_sub.original_text, last_sub.original_text]
                )
                last_prev_sub.translated_text = "\n".join(
                    [last_prev_sub.translated_text, last_sub.translated_text]
                )
                optimized_subtitles.pop()
                evaluate_speed_ratio(last_prev_sub)
                last_sub = last_prev_sub
            else:
                need_gap = (
                    last_sub.tts_eval_speed_ratio
                    * last_sub.tts_expected_duration_ms
                    / last_sub.tts_expected_speed_ratio
                ) - last_sub.tts_expected_duration_ms
                need_gap = max(0, need_gap)
                last_sub.start_ms -= int(min(gap, need_gap))
                evaluate_speed_ratio(last_sub)
                break

        ctx.optimized_subtitles = optimized_subtitles

    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        ctx.optimized_subtitles = [SubtitleLine(**item) for item in log_data]
        return True

    def logfile_name(self) -> str:
        return "optimized_subtitles"
    
    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx: ProcessingContext) -> list[dict]:
        return [asdict(item) for item in ctx.optimized_subtitles]

    def set_data(self, ctx: ProcessingContext, data: list[dict]) -> None:
        ctx.optimized_subtitles = [SubtitleLine(**item) for item in data]

    def self_check(self, ctx) -> list[SelfCheckItem]:
        # 检查是否有优化后的字幕仍然过长
        check_results = []
        for i, sub in enumerate(ctx.optimized_subtitles):
            if sub.tts_duration_rating == DurationRating.TOO_LONG:
                check_results.append(
                    SelfCheckItem(
                        index=i,
                        check_point="tts_duration_rating",
                        issue=f"优化后的字幕仍然过长（{sub.tts_eval_speed_ratio}），原文：{sub.original_text}",
                        warning_content=sub.translated_text,
                        confirm_content=sub.translated_text,
                    )
                )

        return check_results

    def check_confirm(self, ctx, data: list[SelfCheckItem]) -> None:
        for item in data:
            ctx.optimized_subtitles[item.index].translated_text = item.confirm_content
            evaluate_speed_ratio(ctx.optimized_subtitles[item.index])





class OptimizeSubtitlesWithoutSpeedCheckStage(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        optimized_subtitles = []
        prev_sub = None
        for sub in ctx.subtitles:
            # 克隆一份，避免修改原始字幕数据
            sub = SubtitleLine(**asdict(sub))
            if prev_sub:
                gap = sub.start_ms - prev_sub.end_ms
                prev_sub.end_ms+= min(gap, 500)
            optimized_subtitles.append(sub)
            prev_sub = sub
        ctx.optimized_subtitles = optimized_subtitles

    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        ctx.optimized_subtitles = [SubtitleLine(**item) for item in log_data]
        return True

    def logfile_name(self) -> str:
        return "optimized_subtitles"
    
    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx: ProcessingContext) -> list[dict]:
        return [asdict(item) for item in ctx.optimized_subtitles]

    def set_data(self, ctx: ProcessingContext, data: list[dict]) -> None:
        ctx.optimized_subtitles = [SubtitleLine(**item) for item in data]

    def self_check(self, ctx) -> list[SelfCheckItem]:
        pass

    def check_confirm(self, ctx, data: list[SelfCheckItem]) -> None:
        pass

