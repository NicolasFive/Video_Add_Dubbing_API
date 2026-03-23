from pathlib import Path
from app.core.exceptions import FileProcessingError
from app.utils.cmd_runner import CmdRunner
import json
import logging

logger = logging.getLogger(__name__)



def get_audio_duration(audio_path: Path) -> float:
    """
    获取音频文件的时长（秒）

    使用 ffprobe 获取音频时长信息

    :param audio_path: 音频文件路径
    :return: 时长（秒）
    :raises FileProcessingError: 如果 ffprobe 执行失败
    """
    try:
        # 使用 -print_format json 获取结构化输出，更兼容不同版本的 ffprobe
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-print_format",
            "json",
            str(audio_path),
        ]
        output = CmdRunner.run(cmd)
        result = json.loads(output)
        duration = float(result["format"]["duration"])
        logger.info(f"Audio duration: {duration:.3f}s for {audio_path}")
        return duration
    except (ValueError, IndexError, KeyError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse duration: {e}")
        raise FileProcessingError(f"Failed to parse audio duration: {e}")