from app.utils.cmd_runner import CmdRunner
from pathlib import Path
import ffmpeg
import os


class FFmpegBurner:
    def burn(
        self,
        video_path: str,
        subtitle_path: str,
        output_path: str,
        video_width=None,
        video_height=None,
        subtitle_font_size=None,
    ):
        subtitle_font_size=54
        # ffmpeg -i input.mp4 -vf subtitles=sub.srt output.mp4
        # 注意：中文字幕需要指定字体，否则可能乱码
        v_path = self._modify_separator(video_path)
        s_path = self._modify_separator(subtitle_path)
        o_path = self._modify_separator(output_path)

        safe_s_path = s_path.replace("'", r"\'")

        # 计算动态描边宽度
        # libass 的 Outline 单位也是像素 (当 PlayRes 匹配时)
        outline_width = int(subtitle_font_size * 0.12)
        shadow_depth = int(subtitle_font_size * 0.05) # 阴影深度

        # 根据视频宽高设置 PlayRes，确保字幕相对大小
        if video_width>video_height:
            video_width = 1920
            video_height = 1080
        else:
            video_width = 1080
            video_height = 1920
        style_configs = [
            f"FontSize={subtitle_font_size}",
            f"PlayResX={video_width}",       # 强制匹配视频分辨率，防止缩放模糊
            f"PlayResY={video_height}",
            "BorderStyle=1",        # 1=矢量描边 (最清晰), 3=不透明盒 (老式)
            f"Outline={outline_width}", # 关键：增加描边宽度
            f"Shadow={shadow_depth}",   # 关键：增加轻微阴影
        ]

        style_string = ",".join(style_configs)

        ffmpeg.input(v_path).output(
            o_path,
            vf=f"subtitles='{safe_s_path}':force_style='{style_string}'",  # 使用ass滤镜添加字幕
            vcodec="libx264",  # 重新编码视频以嵌入字幕
            acodec="aac",
        ).run(overwrite_output=True)

    def _modify_separator(self, path, new_sep="/") -> str:
        if os.sep != new_sep:
            return path.replace(os.sep, new_sep)
        return path
