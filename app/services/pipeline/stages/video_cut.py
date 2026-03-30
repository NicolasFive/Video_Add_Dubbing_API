from dataclasses import asdict
from app.models.domain import ProcessingContext, SelfCheckItem
from app.utils.audio_utils import get_audio_duration
from app.services.pipeline.base import BasePipelineStage
from app.services.video.cutter import FFmpegVideoCutter, VideoDeleteSegment
from app.utils.time_utils import ms_to_srt_time
import json


class MarkSegmentBySubtitlesStage(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        # 根据字幕时长，标记没有字幕的视频区间，供后续视频裁剪使用。
        delete_segments = []
        begin_ms = 0
        for i, sub in enumerate(ctx.optimized_subtitles):
            # 用实际的tts音频时长来标记字幕区间，避免因为文本长度和语速计算的预估时长不准确导致裁剪点错误。
            duration_sec = get_audio_duration(sub.translated_tts_path)
            start_ms = sub.start_ms
            end_ms = start_ms + int(duration_sec * 1000)
            # 1. 开头不标记，避免裁剪导致视频开头不自然。
            if i == 0:
                begin_ms = end_ms
                continue
            # 2. 标记字幕之间的空白区间，供后续裁剪使用。
            if start_ms > begin_ms:
                delete_segments.append(
                    VideoDeleteSegment(start_ms=begin_ms, end_ms=start_ms)
                )
            begin_ms = end_ms
        # 3. 结尾标记
        duration_sec = get_audio_duration(ctx.instrumentals_audio_path)
        end_ms = int(duration_sec * 1000)
        if end_ms > begin_ms:
            delete_segments.append(VideoDeleteSegment(start_ms=begin_ms, end_ms=end_ms))
        ctx.delete_segments = delete_segments

    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        ctx.delete_segments = [VideoDeleteSegment(**item) for item in log_data]
        return True

    def logfile_name(self) -> str:
        return "delete_segments"
    
    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx) -> list[dict]:
        return [asdict(item) for item in ctx.delete_segments]

    def set_data(self, ctx, data: list[dict]):
        ctx.delete_segments = [VideoDeleteSegment(**item) for item in data]

    def self_check(self, ctx) -> list[SelfCheckItem]:
        # 判断是否存在裁剪超长的片段，避免导致视频内容出现较大缺失。
        check_results = []
        for segment in ctx.delete_segments:
            duration_sec = (segment.end_ms - segment.start_ms) / 1000
            if (
                duration_sec > 5
            ):  # 超过3秒的删除片段可能会导致视频内容缺失过多，提示用户确认。
                check_results.append(
                    SelfCheckItem(
                        index=0,
                        check_point="duration",
                        issue=f"检测到一个删除片段时长为{duration_sec:.2f}秒，可能会导致视频内容缺失过多，请确认是否需要删除。",
                        warning_content=f"删除片段：{ms_to_srt_time(segment.start_ms)}({segment.start_ms}毫秒) --> {ms_to_srt_time(segment.end_ms)}({segment.end_ms}毫秒)",
                        confirm_content=json.dumps(asdict(segment)),
                    )
                )
        return check_results

    def check_confirm(self, ctx, data: list[SelfCheckItem]):
        for item in data:
            if item.confirm_content:
                segment_dict = json.loads(item.confirm_content)
                segment = VideoDeleteSegment(**segment_dict)
                ctx.delete_segments[item.index] = segment


class VideoCutByFFmpegStage(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        cutter = FFmpegVideoCutter(ctx.final_video_path or ctx.input_video_path)
        cutter.delete(ctx.delete_segments)

    def restore(self, ctx: ProcessingContext) -> bool:
        pass

    def logfile_name(self) -> str:
        pass
    
    def save_log(self, ctx: ProcessingContext) -> None:
        pass
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass

    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass
