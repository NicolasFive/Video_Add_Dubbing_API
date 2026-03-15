from __future__ import annotations

from app.services.pipeline_stages.base import PipelineStageConfig
from app.services.pipeline_stages.implementations import (
    AnalyzeVideoStage,
    BuildSubtitlesDataStage,
    BurnSubtitlesStage,
    GenerateSubtitlesStage,
    MixAudioStage,
    ReduceTextStage,
    ReplaceAudioStage,
    SeparateVocalsStage,
    SynthesizeVoiceStage,
    TranscribeStage,
    TranslateStage,
)

STAGE_BUILDERS = {
    "analyze_video": AnalyzeVideoStage,
    "separate_vocals": SeparateVocalsStage,
    "transcribe": TranscribeStage,
    "translate": TranslateStage,
    "build_subtitles_data": BuildSubtitlesDataStage,
    "reduce_text": ReduceTextStage,
    "synthesize_voice": SynthesizeVoiceStage,
    "mix_audio": MixAudioStage,
    "replace_audio": ReplaceAudioStage,
    "generate_subtitles": GenerateSubtitlesStage,
    "burn_subtitles": BurnSubtitlesStage,
}

DEFAULT_STAGE_CONFIGS = [
    PipelineStageConfig("analyze_video", "Analyzing Video", 5),
    PipelineStageConfig("separate_vocals", "Separating Vocals", 10),
    PipelineStageConfig("transcribe", "Transcribing", 20),
    PipelineStageConfig("translate", "Translating", 30),
    PipelineStageConfig("build_subtitles_data", "Building Subtitles Data", 40),
    PipelineStageConfig("synthesize_voice", "Synthesizing Voice", 50),
    PipelineStageConfig("mix_audio", "Mixing Audio", 60),
    PipelineStageConfig("replace_audio", "Replacing Audio", 70),
    PipelineStageConfig("generate_subtitles", "Generating Subtitles", 80),
    PipelineStageConfig("burn_subtitles", "Burning Subtitles", 90),
]

OPTIONAL_STAGE_CONFIGS = [
    PipelineStageConfig("reduce_text", "Reducing Text", 45),
]


def build_stage_registry():
    return {key: stage_cls() for key, stage_cls in STAGE_BUILDERS.items()}


def build_default_stage_configs(include_optional: bool = False):
    configs = list(DEFAULT_STAGE_CONFIGS)
    if include_optional:
        configs.extend(OPTIONAL_STAGE_CONFIGS)
    return configs
