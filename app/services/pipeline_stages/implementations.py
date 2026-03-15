from __future__ import annotations

import json
import logging
import re

import ffmpeg

from app.models.domain import (
    DurationRating,
    ProcessingContext,
    ReducerData,
    Sentiment,
    SubtitleLine,
    TranscriptLine,
    TranslateLine,
)
from app.services.audio.mixer import AudioMixer
from app.services.audio.replacer import VideoAudioReplacer
from app.services.audio.separator import DemucsService
from app.services.subtitle.burner import SubtitleBurner
from app.services.subtitle.generator import SubtitleGenerator
from app.services.timing.speed_ratio import SpeedRatioChecker
from app.services.transcription.assemblyai_client import AssemblyAIService
from app.services.translation.llm_reducer import LLMReducer
from app.services.translation.llm_translator import LLMTranslator
from app.services.tts.volcano_tts import VolcanoTTSService, get_volcengine_params

from .base import BasePipelineStage

logger = logging.getLogger(__name__)


class AnalyzeVideoStage(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        width, height = self._get_video_dimensions(ctx.input_video_path)
        ctx.subtitle_font_size = self._cal_subtitle_font_size(width, height)
        ctx.input_video_width = width
        ctx.input_video_height = height

    @staticmethod
    def _get_video_dimensions(video_path) -> tuple[int, int]:
        # 使用ffprobe获取视频信息
        probe = ffmpeg.probe(video_path)
        # 查找视频流
        video_stream = None
        for stream in probe["streams"]:
            if stream["codec_type"] == "video":
                video_stream = stream
                break

        if not video_stream:
            raise ValueError("未找到视频流")
        # 获取宽度和高度
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        return width, height

    @staticmethod
    def _cal_subtitle_font_size(video_width: int, video_height: int) -> int:
        # 根据视频分辨率动态计算字幕字体大小，保持在不同设备上的可读性和美观性
        # 判断是否是竖屏视频，根据视频高度动态计算字体大小，保持字幕在不同分辨率下的可读性和美观性
        is_portrait = video_height > video_width
        if is_portrait:
            # 竖屏视频，字体大小取视频高度的1/20，最小24

            return max(24, video_height // 20)
        # 横屏视频，字体大小取视频高度的1/25，最小16
        return max(16, video_height // 25)


class SeparateVocalsStage(BasePipelineStage):
    def __init__(self, separator: DemucsService | None = None):
        self.separator = separator or DemucsService()

    def run(self, ctx: ProcessingContext) -> None:
        audio_path = (
            ctx.input_audio_path
            if ctx.input_audio_path is not None
            else ctx.input_video_path
        )
        vocals_path, inst_path = self.separator.separate(audio_path, ctx.work_dir)
        ctx.vocals_audio_path = vocals_path
        ctx.instrumentals_audio_path = inst_path


class TranscribeStage(BasePipelineStage):
    def __init__(self, transcriber: AssemblyAIService | None = None):
        self.transcriber = transcriber or AssemblyAIService()

    def run(self, ctx: ProcessingContext) -> None:
        transcribe_log_path = ctx.work_dir / "transcribe_log.json"
        raw_data = self.transcriber.transcribe(
            ctx.vocals_audio_path, transcribe_log_path
        )
        ctx.transcripts = self._parse_transcript(raw_data)

    @staticmethod
    def _parse_transcript(raw_data: dict) -> list[TranscriptLine]:
        # 解析 AssemblyAI 返回的 sentiment_analysis_results 为 TranscriptLine 对象
        sentiment_analysis_results = raw_data.get("sentiment_analysis_results", [])
        result = []
        for item in sentiment_analysis_results:
            s_text = item.get("text", "")
            start = item.get("start", 0)
            end = item.get("end", 0)
            try:
                sentiment = Sentiment(item.get("sentiment", Sentiment.NEUTRAL.value))
            except ValueError:
                sentiment = Sentiment.NEUTRAL
            result.append(
                TranscriptLine(
                    text=s_text, start_ms=start, end_ms=end, sentiment=sentiment
                )
            )
        return result


class TranslateStage(BasePipelineStage):
    def __init__(self, translator: LLMTranslator | None = None):
        self.translator = translator or LLMTranslator()

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
        self._save_translation_log(ctx)

    @staticmethod
    def _save_translation_log(ctx: ProcessingContext) -> None:
        translation_log_path = ctx.work_dir / "translation_log.json"
        log_data = []
        for item in ctx.translations:
            log_data.append(
                {
                    "original_text": item.original_text,
                    "translated_text": item.translated_text,
                }
            )
        with open(translation_log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)


class BuildSubtitlesDataStage(BasePipelineStage):
    def __init__(self, speed_ratio_checker: SpeedRatioChecker | None = None):
        self.speed_ratio_checker = speed_ratio_checker or SpeedRatioChecker()

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

        ctx.subtitles = raw_subtitles
        self._save_subtitles_log(ctx, suffix="raw")
        # 根据 sub.tts_duration_rating 处理播放速率过快或过慢的字幕，调整策略可以包括：
        # 1. 过长：尝试精简表达方式
        # 2. 过长：尝试利用相邻字幕间隙时间，增加目标时长
        # 3. 过长：尝试合并相邻字幕，增加目标时长
        # 4. 过短：暂时不做处理
        handled_subtitles = []
        prev_sub = None
        for sub in raw_subtitles:
            # 判断是否与前一条超长字幕首尾相连，是则合并文本和时长
            if prev_sub and prev_sub.tts_duration_rating == DurationRating.TOO_LONG:
                gap = sub.start_ms - prev_sub.end_ms
                if gap < 500:  # 如果两条字幕间隔小于500ms，认为是首尾相连
                    # 合并文本和时长
                    prev_sub.end_ms = sub.end_ms
                    prev_sub.text = "\n".join([prev_sub.text, sub.text])
                    # 更新评估数据
                    self._evaluate_speed_ratio(prev_sub)
                    continue  # 当前字幕已经被合并，不再单独添加到列表
                # 如果两条字幕间隔较大，则不合并，尝试利用字幕的间隙
                # 增加字幕时长（时间轴向后）
                need_gap = (
                    prev_sub.tts_eval_speed_ratio
                    * prev_sub.tts_expected_duration_ms
                    / prev_sub.tts_expected_speed_ratio
                ) - prev_sub.tts_expected_duration_ms
                need_gap = max(0, need_gap)
                prev_sub.end_ms += int(min(gap, need_gap))
                # 更新评估数据
                self._evaluate_speed_ratio(prev_sub)

            handled_subtitles.append(sub)
            prev_sub = sub

        if not handled_subtitles:
            ctx.subtitles = handled_subtitles
            self._save_subtitles_log(ctx)
            return
# 处理最后一个字幕，如果它仍然过长则合并至前一个字幕
        last_sub = handled_subtitles[-1]
        while (
            last_sub
            and last_sub.tts_duration_rating == DurationRating.TOO_LONG
            and len(handled_subtitles) > 1
        ):
            last_prev_sub = handled_subtitles[-2]
        # 判断是否与前一条超长字幕首尾相连，是则合并文本和时长
            gap = last_sub.start_ms - last_prev_sub.end_ms
            if gap < 500:# 如果两条字幕间隔小于500ms，认为是首尾相连
                last_prev_sub.end_ms = last_sub.end_ms
                last_prev_sub.text = "\n".join([last_prev_sub.text, last_sub.text])
                handled_subtitles.pop()# 移除最后一个字幕，因为它已经被合并了
                self._evaluate_speed_ratio(last_prev_sub)
                last_sub = last_prev_sub
            else:
                # 如果两条字幕间隔较大，则不合并，尝试利用字幕的间隙
                # 增加字幕的时长（时间轴向前）
                need_gap = (
                    last_sub.tts_eval_speed_ratio
                    * last_sub.tts_expected_duration_ms
                    / last_sub.tts_expected_speed_ratio
                ) - last_sub.tts_expected_duration_ms
                need_gap = max(0, need_gap)
                last_sub.start_ms -= int(min(gap, need_gap))
                # 更新评估数据
                self._evaluate_speed_ratio(last_sub)
                break

        ctx.subtitles = handled_subtitles
        self._save_subtitles_log(ctx)

    def _evaluate_speed_ratio(self, sub: SubtitleLine) -> None:
        # 1. 计算TTS播放时长
        duration_ms = sub.tts_expected_duration_ms
        # 2. 根据TTS文本和播放时长，计算得到TTS播放速率
        translated_params = get_volcengine_params(sub.text, duration_ms / 1000)
        translated_speed_ratio = translated_params.speed_ratio
        # 3. 评估TTS播放速率等级，并给出满足正常水平的目标速率
        duration_rating, target_ratio = self.speed_ratio_checker.check(
            translated_speed_ratio
        )
        # 赋值
        sub.tts_duration_rating = duration_rating
        sub.tts_expected_speed_ratio = target_ratio
        sub.tts_eval_speed_ratio = translated_speed_ratio

    @staticmethod
    def _save_subtitles_log(ctx: ProcessingContext, suffix: str = "") -> None:
        subtitles_log_path = ctx.work_dir / f"subtitles_log_{suffix}.json"
        log_data = []
        for sub in ctx.subtitles:
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
        with open(subtitles_log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)


class ReduceTextStage(BasePipelineStage):
    def __init__(self, reducer: LLMReducer | None = None):
        self.reducer = reducer or LLMReducer()

    def run(self, ctx: ProcessingContext) -> None:
        reducer_data_list = []
        for sub in ctx.subtitles:
            if sub.tts_duration_rating == DurationRating.TOO_LONG:
                # 计算在目标速率下，字幕文本需要到多少字符长度
                # proportion 为需要保留的字符比例
                proportion = sub.tts_expected_speed_ratio / sub.tts_eval_speed_ratio
                text_len = len(sub.text)
                expected_text_len = max(1, int(text_len * proportion))# 避免出现小于1的字符长度
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
                expected_text_len = reducer_data_list[reduced_index].target_length
                if len(reduced_text) <= expected_text_len:
                    sub.tts_duration_rating = None# 已经处理好，不再标记为过长
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


class SynthesizeVoiceStage(BasePipelineStage):
    def __init__(self, tts: VolcanoTTSService | None = None):
        self.tts = tts or VolcanoTTSService()

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
                sub.text,
                sub.tts_expected_duration_ms,
                tts_path,
                voice_type=ctx.voice_type,
                emotion=emotion,
            )
            sub.translated_tts_path = tts_path

    @staticmethod
    def _check_speech_text_is_blank(text: str) -> bool:
        # 判断文本是否只包含不可读文本（如标点）
        readable_content = re.sub(r"[^\w\s]", "", text)
        return len(readable_content.strip()) == 0


class MixAudioStage(BasePipelineStage):
    def __init__(self, audio_mixer: AudioMixer | None = None):
        self.audio_mixer = audio_mixer or AudioMixer()

    def run(self, ctx: ProcessingContext) -> None:
        mixed_audio_path = ctx.work_dir / "mixed_audio.wav"
        self.audio_mixer.init_voice(str(ctx.instrumentals_audio_path))
        for sub in ctx.subtitles:
            if sub.translated_tts_path:
                logger.info(
                    "Adding overlay: %s %s",
                    str(sub.start_ms),
                    str(sub.translated_tts_path),
                )
                self.audio_mixer.add_overlay(
                    str(sub.translated_tts_path),
                    start_time_ms=sub.start_ms,
                )
        self.audio_mixer.export(str(mixed_audio_path))


class ReplaceAudioStage(BasePipelineStage):
    def __init__(self, replacer: VideoAudioReplacer | None = None):
        self.replacer = replacer or VideoAudioReplacer()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        video_with_dubbing = ctx.work_dir / "video_with_dubbing.mp4"
        mixed_audio_path = ctx.work_dir / "mixed_audio.wav"
        self.replacer.replace(
            ctx.input_video_path, mixed_audio_path, video_with_dubbing
        )


class GenerateSubtitlesStage(BasePipelineStage):
    def __init__(self, sub_gen: SubtitleGenerator | None = None):
        self.sub_gen = sub_gen or SubtitleGenerator()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        srt_path = ctx.work_dir / "subtitles.srt"
        self.sub_gen.generate_srt(
            ctx.subtitles,
            srt_path,
            ctx.input_video_width,
            ctx.subtitle_font_size,
        )
        ctx.final_subtitle_path = srt_path


class BurnSubtitlesStage(BasePipelineStage):
    def __init__(self, sub_burner: SubtitleBurner | None = None):
        self.sub_burner = sub_burner or SubtitleBurner()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        video_with_dubbing = ctx.work_dir / "video_with_dubbing.mp4"
        srt_path = ctx.work_dir / "subtitles.srt"
        final_video_path = ctx.work_dir / "final_video_path.mp4"
        self.sub_burner.burn(
            video_with_dubbing,
            srt_path,
            final_video_path,
            ctx.input_video_width,
            ctx.input_video_height,
            ctx.subtitle_font_size,
        )
        ctx.final_video_path = final_video_path
