from app.services.pipeline.stages.analyze_video import FFprobeAnalyzeVideoStage
from app.services.pipeline.stages.build_subtitles_data import (
    OptimizeSubtitlesStage,
    BuildSubtitlesStage,
    OptimizeSubtitlesWithoutSpeedCheckStage
)
from app.services.pipeline.stages.burn_subtitles import FFmpegBurnSubtitlesStage
from app.services.pipeline.stages.generate_subtitles import (
    RuleBasedGenerateSubtitlesStage,
)
from app.services.pipeline.stages.mix_audio import PydubMixAudioStage
from app.services.pipeline.stages.reduce_text import OpenAIReduceTextStage
from app.services.pipeline.stages.replace_audio import FFmpegReplaceAudioStage
from app.services.pipeline.stages.separate_vocals import DemucsSeparateVocalsStage
from app.services.pipeline.stages.synthesize_voice import (
    VolcengineSynthesizeVoiceStage,
    VolcengineV2SynthesizeVoiceStage,
)
from app.services.pipeline.stages.transcribe import AssemblyAITranscribeStage
from app.services.pipeline.stages.translate import OpenAITranslateStage
from app.services.pipeline.stages.complete import CompleteStage
from app.services.pipeline.stages.emotion_analysis import EmotionAnalysisBySentimentStage
from app.services.pipeline.stages.replace_audio import FFmpegOriginalSwapStage
from app.services.pipeline.stages.video_cut import (
    MarkSegmentBySubtitlesStage,
    VideoCutByFFmpegStage,
)
from app.services.pipeline.stages.prepare import PrepareForBeginning


__all__ = [
    "FFprobeAnalyzeVideoStage",
    "DemucsSeparateVocalsStage",
    "AssemblyAITranscribeStage",
    "OpenAITranslateStage",
    "BuildSubtitlesStage",
    "OptimizeSubtitlesStage",
    "OpenAIReduceTextStage",
    "VolcengineSynthesizeVoiceStage",
    "VolcengineV2SynthesizeVoiceStage",
    "PydubMixAudioStage",
    "FFmpegReplaceAudioStage",
    "RuleBasedGenerateSubtitlesStage",
    "FFmpegBurnSubtitlesStage",
    "CompleteStage",
    "FFmpegOriginalSwapStage",
    "OptimizeSubtitlesWithoutSpeedCheckStage",
    "MarkSegmentBySubtitlesStage",
    "VideoCutByFFmpegStage",
    "EmotionAnalysisBySentimentStage",
    "PrepareForBeginning",
]
