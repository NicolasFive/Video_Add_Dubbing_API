from __future__ import annotations

from app.services.pipeline.base import PipelineStageConfig
from app.services.pipeline.stages import (
    FFprobeAnalyzeVideoStage,
    DemucsSeparateVocalsStage,
    AssemblyAITranscribeStage,
    OpenAITranslateStage,
    RuleBasedBuildSubtitlesDataStage,
    OpenAIReduceTextStage,
    VolcengineSynthesizeVoiceStage,
    VolcengineV2SynthesizeVoiceStage,
    PydubMixAudioStage,
    FFmpegReplaceAudioStage,
    RuleBasedGenerateSubtitlesStage,
    FFmpegBurnSubtitlesStage,
)
STAGE_BUILDERS = {
    "analyze_video": FFprobeAnalyzeVideoStage,
    "separate_vocals": DemucsSeparateVocalsStage,
    "transcribe": AssemblyAITranscribeStage,
    "translate": OpenAITranslateStage,
    "build_subtitles_data": RuleBasedBuildSubtitlesDataStage,
    "reduce_text": OpenAIReduceTextStage,
    "synthesize_voice": VolcengineSynthesizeVoiceStage,
    "synthesize_voice_v2": VolcengineV2SynthesizeVoiceStage,
    "mix_audio": PydubMixAudioStage,
    "replace_audio": FFmpegReplaceAudioStage,
    "generate_subtitles": RuleBasedGenerateSubtitlesStage,
    "burn_subtitles": FFmpegBurnSubtitlesStage,
}

DEFAULT_STAGE_CONFIGS = [
    PipelineStageConfig("analyze_video", "Analyzing Video", 5),
    PipelineStageConfig("separate_vocals", "Separating Vocals", 10),
    PipelineStageConfig("transcribe", "Transcribing", 20),
    PipelineStageConfig("translate", "Translating", 30),
    PipelineStageConfig("build_subtitles_data", "Building Subtitles Data", 40),
    PipelineStageConfig("synthesize_voice_v2", "Synthesizing Voice", 50),
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
