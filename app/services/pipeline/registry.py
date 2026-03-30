from __future__ import annotations

from app.services.pipeline.base import PipelineStageConfig
from app.services.pipeline.stages import (
    FFprobeAnalyzeVideoStage,
    DemucsSeparateVocalsStage,
    AssemblyAITranscribeStage,
    OpenAITranslateStage,
    OptimizeSubtitlesStage,
    BuildSubtitlesStage,
    OpenAIReduceTextStage,
    VolcengineSynthesizeVoiceStage,
    VolcengineV2SynthesizeVoiceStage,
    PydubMixAudioStage,
    FFmpegReplaceAudioStage,
    RuleBasedGenerateSubtitlesStage,
    FFmpegBurnSubtitlesStage,
    CompleteStage,
    FFmpegOriginalSwapStage,
    OptimizeSubtitlesWithoutSpeedCheckStage,
    MarkSegmentBySubtitlesStage,
    VideoCutByFFmpegStage,
    EmotionAnalysisBySentimentStage,
)
STAGE_BUILDERS = {
    "Analyzing Video": FFprobeAnalyzeVideoStage,
    "Separating Vocals": DemucsSeparateVocalsStage,
    "Transcribing": AssemblyAITranscribeStage,
    "Translating": OpenAITranslateStage,
    "Building Subtitles": BuildSubtitlesStage,
    "Optimizing Subtitles": OptimizeSubtitlesStage,
    "Optimizing Subtitles Without Speed Check": OptimizeSubtitlesWithoutSpeedCheckStage,
    "Reducing Text": OpenAIReduceTextStage,
    "Emotion Analysis": EmotionAnalysisBySentimentStage,
    "Synthesizing Voice": VolcengineSynthesizeVoiceStage,
    "Synthesizing Voice V2": VolcengineV2SynthesizeVoiceStage,
    "Mixing Audio": PydubMixAudioStage,
    "Replacing Audio": FFmpegReplaceAudioStage,
    "Generating Subtitles": RuleBasedGenerateSubtitlesStage,
    "Burning Subtitles": FFmpegBurnSubtitlesStage,
    "Original Swap": FFmpegOriginalSwapStage,
    "Mark Delete Segment": MarkSegmentBySubtitlesStage,
    "Video Cutting": VideoCutByFFmpegStage,
    "Complete": CompleteStage,
}

DOUBAO_V1_STAGE_CONFIGS = [
    PipelineStageConfig("Analyzing Video", "分析视频", 5),
    PipelineStageConfig("Separating Vocals", "分离人声", 10),
    PipelineStageConfig("Transcribing", "转录", 20),
    PipelineStageConfig("Translating", "翻译", 30),
    PipelineStageConfig("Building Subtitles", "生成字幕数据", 40),
    PipelineStageConfig("Optimizing Subtitles", "优化字幕数据", 48),
    PipelineStageConfig("Synthesizing Voice", "豆包语音合成1.0", 50),
    PipelineStageConfig("Mixing Audio", "混合音频", 60),
    PipelineStageConfig("Replacing Audio", "替换音频", 70),
    PipelineStageConfig("Generating Subtitles", "生成字幕", 80),
    PipelineStageConfig("Burning Subtitles", "烧录字幕", 90),
    PipelineStageConfig("Original Swap", "原声置换", 95),
    PipelineStageConfig("Complete", "完成", 100),
]


DOUBAO_V2_STAGE_CONFIGS = [
    PipelineStageConfig("Analyzing Video", "分析视频", 5),
    PipelineStageConfig("Separating Vocals", "分离人声", 10),
    PipelineStageConfig("Transcribing", "转录", 20),
    PipelineStageConfig("Translating", "翻译", 30),
    PipelineStageConfig("Building Subtitles", "生成字幕", 40),
    PipelineStageConfig("Optimizing Subtitles", "优化字幕", 48),
    PipelineStageConfig("Emotion Analysis", "情绪分析", 49),
    PipelineStageConfig("Synthesizing Voice V2", "豆包语音合成2.0", 50),
    PipelineStageConfig("Mixing Audio", "混合音频", 60),
    PipelineStageConfig("Replacing Audio", "替换音频", 70),
    PipelineStageConfig("Generating Subtitles", "生成字幕", 80),
    PipelineStageConfig("Burning Subtitles", "烧录字幕", 90),
    PipelineStageConfig("Original Swap", "原声置换", 95),
    PipelineStageConfig("Mark Delete Segment", "标记删除片段", 96),
    PipelineStageConfig("Video Cutting", "视频裁剪", 97),
    PipelineStageConfig("Complete", "完成", 100),
]

ONLY_SUBTITLES_STAGE_CONFIGS = [
    PipelineStageConfig("Analyzing Video", "分析视频", 5),
    PipelineStageConfig("Separating Vocals", "分离人声", 10),
    PipelineStageConfig("Transcribing", "转录", 20),
    PipelineStageConfig("Translating", "翻译", 30),
    PipelineStageConfig("Building Subtitles", "生成字幕", 40),
    PipelineStageConfig("Optimizing Subtitles Without Speed Check", "优化字幕（无音速检查）", 48),
    PipelineStageConfig("Replacing Audio", "替换音频", 70),
    PipelineStageConfig("Generating Subtitles", "生成字幕", 80),
    PipelineStageConfig("Burning Subtitles", "烧录字幕", 90),
    PipelineStageConfig("Complete", "完成", 100),
]


# 预设多个 STAGE_CONFIGS
STAGE_CONFIGS_MAP = {
    "default": DOUBAO_V2_STAGE_CONFIGS,
    "doubao_v1": DOUBAO_V1_STAGE_CONFIGS,
    "doubao_v2": DOUBAO_V2_STAGE_CONFIGS,
    "only_subtitles": ONLY_SUBTITLES_STAGE_CONFIGS,
}


def build_stage_registry():
    return {key: stage_cls() for key, stage_cls in STAGE_BUILDERS.items()}


def get_available_line_types() -> list[str]:
    """获取所有可用的 line_type"""
    return list(STAGE_CONFIGS_MAP.keys())


def build_stage_configs(line_type: str = "default") -> list[PipelineStageConfig]:
    """根据 line_type 构建对应的 STAGE_CONFIGS
    
    Args:
        line_type: 配置类型，如果不存在则使用默认值
        
    Returns:
        对应 line_type 的 STAGE_CONFIGS 列表
    """
    if line_type not in STAGE_CONFIGS_MAP:
        line_type = "default"
    configs = list(STAGE_CONFIGS_MAP[line_type])
    return configs
