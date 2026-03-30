from __future__ import annotations
from pathlib import Path
from app.models.domain import ProcessingContext, Sentiment, TranscriptLine
from app.services.transcription.assemblyai_client import AssemblyAIService
import json
from app.services.pipeline.base import BasePipelineStage


class AssemblyAITranscribeStage(BasePipelineStage):
    def __init__(self):
        self.transcriber = AssemblyAIService()
        self.transcript_json = {}

    def run(self, ctx: ProcessingContext) -> None:
        result = self.transcriber.transcribe(ctx.vocals_audio_path)
        raw_data = result.json_response
        self.transcript_json = raw_data
        ctx.transcripts = self._parse_transcript(raw_data)
        
    def restore(self, ctx: ProcessingContext) -> bool:
        log_data = self.read_log(ctx)
        if not log_data:
            return False
        log_data = json.loads(log_data)
        self.transcript_json = log_data
        ctx.transcripts = self._parse_transcript(log_data)
        return True

    def logfile_name(self) -> str:
        return "transcriptions"
    
    def save_log(self, ctx: ProcessingContext) -> None:
        log_name = self.logfile_name()
        log_data = self.transcript_json
        super()._save_log(ctx, log_name=log_name, log_data=log_data)
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx: ProcessingContext) -> dict:
        log_data = self.read_log(ctx)
        transcript_json = json.loads(log_data)
        return transcript_json

    def set_data(self, ctx, data: dict):
        self.transcript_json = data
    
    def self_check(self, ctx):
        pass

    def check_confirm(self, ctx, data):
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
