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
    FFmpegOriginalSwapStage
)
STAGE_BUILDERS = {
    "Analyzing Video": FFprobeAnalyzeVideoStage,
    "Separating Vocals": DemucsSeparateVocalsStage,
    "Transcribing": AssemblyAITranscribeStage,
    "Translating": OpenAITranslateStage,
    "Building Subtitles": BuildSubtitlesStage,
    "Optimizing Subtitles": OptimizeSubtitlesStage,
    "Reducing Text": OpenAIReduceTextStage,
    "Synthesizing Voice": VolcengineSynthesizeVoiceStage,
    "Synthesizing Voice V2": VolcengineV2SynthesizeVoiceStage,
    "Mixing Audio": PydubMixAudioStage,
    "Replacing Audio": FFmpegReplaceAudioStage,
    "Generating Subtitles": RuleBasedGenerateSubtitlesStage,
    "Burning Subtitles": FFmpegBurnSubtitlesStage,
    "Original Swap": FFmpegOriginalSwapStage,
    "Complete": CompleteStage,
}

DEFAULT_STAGE_CONFIGS = [
    PipelineStageConfig("Analyzing Video", "分析视频", 5),
    PipelineStageConfig("Separating Vocals", "分离人声", 10),
    PipelineStageConfig("Transcribing", "转录", 20),
    PipelineStageConfig("Translating", "翻译", 30),
    PipelineStageConfig("Building Subtitles", "生成字幕", 40),
    PipelineStageConfig("Optimizing Subtitles", "优化字幕", 48),
    PipelineStageConfig("Synthesizing Voice V2", "豆包语音合成2.0", 50),
    # PipelineStageConfig("Synthesizing Voice", "豆包语音合成1.0", 50),
    PipelineStageConfig("Mixing Audio", "混合音频", 60),
    PipelineStageConfig("Replacing Audio", "替换音频", 70),
    PipelineStageConfig("Generating Subtitles", "生成字幕", 80),
    PipelineStageConfig("Burning Subtitles", "烧录字幕", 90),
    PipelineStageConfig("Original Swap", "原声置换", 95),
    PipelineStageConfig("Complete", "完成", 100),
]



def build_stage_registry():
    return {key: stage_cls() for key, stage_cls in STAGE_BUILDERS.items()}


def build_stage_configs()-> list[PipelineStageConfig]:
    configs = list(DEFAULT_STAGE_CONFIGS)
    return configs
