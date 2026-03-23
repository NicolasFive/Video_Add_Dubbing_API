import assemblyai as aai
from pathlib import Path
from app.core.config import settings
import json

class AssemblyAIService:
    def __init__(self):
        aai.settings.api_key = settings.ASSEMBLYAI_KEY

    def transcribe(self, audio_path: str) -> aai.Transcript:
        """转录音频并返回包含时间戳的文本数据"""
        config = aai.TranscriptionConfig(
            speech_models=["universal-3-pro"],
            speaker_labels=True,
            sentiment_analysis=True,
        )
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_path)
        
        if transcript.status == "error":
            raise Exception(f"AssemblyAI Error: {transcript.error}")
        
        return transcript