from __future__ import annotations

import ffmpeg

from app.models.domain import ProcessingContext
import json
from app.services.pipeline.base import BasePipelineStage


class FFprobeAnalyzeVideoStage(BasePipelineStage):
    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        width, height = self._get_video_dimensions(ctx.input_video_path)
        ctx.subtitle_font_size = self._cal_subtitle_font_size(width, height)
        ctx.input_video_width = width
        ctx.input_video_height = height

    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        ctx.input_video_width = log_data.get("width")
        ctx.input_video_height = log_data.get("height")
        ctx.subtitle_font_size = log_data.get("subtitle_font_size")
        return True

    def logfile_name(self) -> str:
        return "video_info"

    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.get_data(ctx)
        super()._save_log(ctx, log_name=log_name, log_data=log_data)

    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)

    def get_data(self, ctx: ProcessingContext) -> dict:
        return {
            "width": ctx.input_video_width,
            "height": ctx.input_video_height,
            "subtitle_font_size": ctx.subtitle_font_size,
        }

    def set_data(self, ctx: ProcessingContext, data: dict) -> None:
        ctx.input_video_width = data.get("width")
        ctx.input_video_height = data.get("height")
        ctx.subtitle_font_size = data.get("subtitle_font_size")

    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass

    @staticmethod
    def _get_video_dimensions(video_path) -> tuple[int, int]:
        # 使用 ffprobe 获取视频信息
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
        # 根据视频分辨率动态计算字幕字体大小
        is_portrait = video_height > video_width
        if is_portrait:
            # 竖屏视频，字体大小取视频高度的 1/20，最小 24
            return max(24, video_height // 20)
        # 横屏视频，字体大小取视频高度的 1/25，最小 16
        return max(16, video_height // 25)
