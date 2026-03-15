import assemblyai as aai
from pathlib import Path
from app.core.config import settings
import json

class AssemblyAIService:
    def __init__(self):
        aai.settings.api_key = settings.ASSEMBLYAI_KEY

    def transcribe(self, audio_path: Path, log_path: Path) -> dict:
        """转录音频并返回包含时间戳的文本数据"""
        config = aai.TranscriptionConfig(
            speech_models=["universal"],
            speaker_labels=True,
            sentiment_analysis=True,
        )
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(str(audio_path))
        
        if transcript.status == "error":
            raise Exception(f"AssemblyAI Error: {transcript.error}")
        
        json_response = transcript.json_response
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(json_response, ensure_ascii=False, indent=2))

        return json_response # 返回原始 JSON 供后续处理