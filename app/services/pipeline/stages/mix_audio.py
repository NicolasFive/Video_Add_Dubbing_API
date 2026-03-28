import logging
from app.models.domain import ProcessingContext
from app.services.audio.mixer import PydubMixAudio
from app.utils.cmd_runner import CmdRunner
from app.services.pipeline.base import BasePipelineStage
from pathlib import Path
import math
from app.utils.audio_utils import get_audio_duration

logger = logging.getLogger(__name__)


class PydubMixAudioStage(BasePipelineStage):
    def __init__(self):
        self.audio_mixer = PydubMixAudio()

    def run(self, ctx: ProcessingContext) -> None:
        mixed_audio_path = Path(ctx.work_dir) / "mixed_audio.wav"
        self.audio_mixer.init_voice(ctx.instrumentals_audio_path)
        for i,sub in enumerate(ctx.optimized_subtitles):
            if sub.translated_tts_path:
                logger.info(
                    "Adding overlay: %s %s",
                    str(sub.start_ms),
                    sub.translated_tts_path,
                )
                # 1. 判断当前TTS的时长是否与下一条存在重叠
                if i < len(ctx.optimized_subtitles) - 1:
                    next_sub = ctx.optimized_subtitles[i + 1]
                    duration_sec = get_audio_duration(Path(sub.translated_tts_path))
                    end_ms = sub.start_ms + duration_sec * 1000
                    if end_ms > next_sub.start_ms:
                        # 存在重叠，计算需要调整的速率
                        adjust_ratio = (duration_sec * 1000 ) / (next_sub.start_ms -sub.start_ms)
                        adjust_ratio = math.ceil(adjust_ratio * 100) / 100  # 保留两位小数
                        logger.info(
                            f"Detected overlap of {end_ms - next_sub.start_ms}ms for subtitle {i}, adjusting speed ratio to {adjust_ratio:.2f}"
                        )
                        # 2. 调整当前TTS的速率，确保不与下一条重叠
                        self.adjust_oversize_audio(
                            Path(sub.translated_tts_path), adjust_ratio
                        )
                # 3. 处理最后一条字幕，如果它的时长超出音频总长度，也需要调整速率
                else:
                    total_duration_sec = get_audio_duration(Path(ctx.instrumentals_audio_path))
                    if sub.start_ms + duration_sec * 1000 > total_duration_sec * 1000:
                        adjust_ratio = (duration_sec * 1000) / (total_duration_sec * 1000 - sub.start_ms)
                        adjust_ratio = math.ceil(adjust_ratio * 100) / 100  # 保留两位小数
                        logger.info(
                            f"Last subtitle {i} exceeds total audio length, adjusting speed ratio to {adjust_ratio:.2f}"
                        )
                        self.adjust_oversize_audio(
                            Path(sub.translated_tts_path), adjust_ratio
                        )

                # 4. 添加叠加
                self.audio_mixer.add_overlay(
                    sub.translated_tts_path,
                    start_time_ms=sub.start_ms,
                    duck_db=ctx.duck_db
                )
        self.audio_mixer.export(str(mixed_audio_path))

    def adjust_oversize_audio(self, audio_path: Path, speed_ratio: float):
        
            # ffmpeg 使用 atempo 滤镜应用速率
            # atempo 的范围是 [0.5, 2.0]
            temp_path = audio_path.with_stem(audio_path.stem + "_temp")

            try:
                cmd = [
                    "ffmpeg",
                    "-i",
                    str(audio_path),
                    "-filter:a",
                    f"atempo={speed_ratio}",
                    "-y",  # 覆盖输出文件
                    str(temp_path),
                ]

                CmdRunner.run(cmd)
                logger.info(
                    f"ffmpeg successfully adjusted audio speed to {speed_ratio:.2f}x"
                )
                # 替换原文件
                temp_path.replace(audio_path)
                logger.info(f"Replaced original audio file: {audio_path}")
            except Exception as e:
                # 清理临时文件
                if temp_path.exists():
                    temp_path.unlink()
                logger.error(f"Failed to adjust audio speed: {e}")
                raise

    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass
    
    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
        pass