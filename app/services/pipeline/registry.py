from __future__ import annotations

from pathlib import Path

import yaml

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
    PrepareForBeginning,
)

STAGE_BUILDERS = {
    "Preparing": PrepareForBeginning,
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

_STAGES_YML = Path(__file__).with_name("pipeline_stages.yml")


def _load_stage_configs_map() -> dict[str, list[PipelineStageConfig]]:
    with _STAGES_YML.open("r", encoding="utf-8") as _f:
        _raw: dict[str, list[dict]] = yaml.safe_load(_f)
    result: dict[str, list[PipelineStageConfig]] = {}
    for line_type, stages in _raw.items():
        result[line_type] = [
            PipelineStageConfig(
                key=stage["key"],
                name=stage["name"],
                progress=int(stage["progress"]),
                enabled=bool(stage.get("enabled", True)),
            )
            for stage in stages
        ]
    return result


# 从 pipeline_stages.yml 初始化
STAGE_CONFIGS_MAP = _load_stage_configs_map()


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
