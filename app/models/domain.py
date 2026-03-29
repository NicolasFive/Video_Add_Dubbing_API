from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from app.services.video.cutter import VideoDeleteSegment


class Sentiment(str, Enum):
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"

class DurationRating(str, Enum):
    TOO_LONG = "TOO_LONG" # 字幕过长，配音可能听起来不自然，语速过快
    TOO_SHORT = "TOO_SHORT" # 字幕过短，配音可能听起来拖沓，语速过慢


@dataclass
class SubtitleLine:
    start_ms: int
    end_ms: int
    original_text: str
    translated_text: str
    sentiment: Optional[Sentiment] = None
    speaker: Optional[str] = None
    # 播放速率及评级
    tts_duration_rating: Optional[DurationRating] = None
    tts_eval_speed_ratio: Optional[float] = None
    tts_expected_speed_ratio: Optional[float] = None

    translated_tts_path: Optional[str] = None

    @property
    def tts_expected_duration_ms(self) -> int:
        return self.end_ms - self.start_ms

@dataclass
class TranscriptLine:
    start_ms: int
    end_ms: int
    text: str
    sentiment: Optional[Sentiment] = None
    speaker: Optional[str] = None

@dataclass
class TranslateLine:
    original_text: str
    translated_text: Optional[str] = None

@dataclass
class ProcessingContext:
    """贯穿整个 Pipeline 的上下文对象"""

    task_id: str
    input_video_path: Optional[str]
    input_audio_path: Optional[str]
    work_dir: str
    voice_types: list[str] = field(default_factory=list)
    line_type: str = "default"  # 用于选择不同的 STAGE_CONFIGS
    duck_db: Optional[int]=-10  # 叠加时主音频的降音量，单位为 dB

    # 当前执行的步骤，用于断点续传
    current_step: Optional[str] = None

    # 中间产物路径
    input_video_width: Optional[int] = None
    input_video_height: Optional[int] = None
    subtitle_font_size: Optional[int] = None
    vocals_audio_path: Optional[str] = None
    instrumentals_audio_path: Optional[str] = None
    transcript_json_path: Optional[str] = None

    # 数据对象
    transcripts: List[TranscriptLine] = field(default_factory=list)
    translations: List[TranslateLine] = field(default_factory=list)
    subtitles: List[SubtitleLine] = field(default_factory=list)
    optimized_subtitles: List[SubtitleLine] = field(default_factory=list)
    video_delete_segments: List[VideoDeleteSegment] = field(default_factory=list)

    # 最终结果
    final_video_path: Optional[str] = None
    final_subtitle_path: Optional[str] = None

@dataclass
class ReducerData:
    text: str
    target_length: int
    reduced_text: Optional[str] = None


@dataclass
class SelfCheckItem:
    index: int
    check_point: str
    issue: str = None
    warning_content: Optional[str] = None
    confirm_content: Optional[str] = None

