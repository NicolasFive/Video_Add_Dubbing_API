from __future__ import annotations

from app.models.domain import ProcessingContext, Sentiment, TranscriptLine
from app.services.transcription.assemblyai_client import AssemblyAIService

from app.services.pipeline.base import BasePipelineStage


class AssemblyAITranscribeStage(BasePipelineStage):
    def __init__(self):
        self.transcriber = AssemblyAIService()

    def run(self, ctx: ProcessingContext) -> None:
        result = self.transcriber.transcribe(ctx.vocals_audio_path)
        raw_data = result.json_response
        self._save_log(ctx, log_name="transcriptions", log_data=raw_data)
        ctx.transcripts = self._parse_transcript(raw_data)
        
    def get_data(self, ctx):
        pass

    def set_data(self, ctx, data):
        pass

    @staticmethod
    def _parse_transcript(raw_data: dict) -> list[TranscriptLine]:
        # 解析 AssemblyAI 返回的 sentiment_analysis_results 为 TranscriptLine 对象
        sentiment_analysis_results = raw_data.get("sentiment_analysis_results", [])
        result = []
        for item in sentiment_analysis_results:
            s_text = item.get("text", "")
            start = item.get("start", 0)
            end = item.get("end", 0)
            speaker = item.get("speaker", "unknown")
            try:
                sentiment = Sentiment(item.get("sentiment", Sentiment.NEUTRAL.value))
            except ValueError:
                sentiment = Sentiment.NEUTRAL
            result.append(
                TranscriptLine(
                    text=s_text, start_ms=start, end_ms=end, sentiment=sentiment, speaker=speaker
                )
            )
        return result
