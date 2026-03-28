from app.services.translation.llm_base import LLMBase
from jinja2 import Template
import json
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EmotionContext(BaseModel):
    positive: str
    negative: str
    neutral: str

class LLMEmotionor(LLMBase):

    def __init__(self):
        super().__init__("app/core/emotion_llm_cfg.json")

    def analyse(self, text: str, max_retries=3) -> EmotionContext:
        retry_count = 0
        success = False
        result = EmotionContext(positive="", negative="", neutral="")
        while retry_count <= max_retries and not success:
            params = {"text": text}
            system_message = Template(self.llm_cfg["sp"]).render(**params)
            user_message = Template(self.llm_cfg["up"]).render(**params)
            messages = []
            messages = self.set_system_message(messages, system_message)
            messages = self.set_user_message(messages, user_message)

            try:
                chat_response = self.chat(messages)
                emotion_contexts = json.loads(chat_response)
                emotion_contexts = (
                    emotion_contexts if isinstance(emotion_contexts, dict) else {}
                )
                result.positive = emotion_contexts.get("POSITIVE", "")
                result.negative = emotion_contexts.get("NEGATIVE", "")
                result.neutral = emotion_contexts.get("NEUTRAL", "")
                success = True
            except Exception as e:
                logger.error(f"Analyse error: {e}")
                retry_count += 1
        if not success:
            logger.error(f"Failed to analyse batch after {max_retries} retries. ")
        return result

    def exec(self, text: str) -> EmotionContext:
        emotion_context = self.analyse(text)
        return emotion_context
