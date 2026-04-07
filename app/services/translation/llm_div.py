from app.models.domain import ReducerData
from app.services.translation.llm_base import LLMBase
from jinja2 import Template
import json
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DivResult(BaseModel):
    original_text: str
    translated_texts: list[str]
    original_texts: list[str]


class LLMDiv(LLMBase):
    def __init__(self):
        super().__init__("app/core/div_llm_cfg.json")

    def divide(self, result: DivResult, max_retries=3) -> None:
        retry_count = 0
        success = False
        while retry_count <= max_retries and not success:
            params = {
                "data": json.dumps(
                    {
                        "original_text": result.original_text,
                        "translated_text": result.translated_texts,
                    },
                    ensure_ascii=False,
                )
            }
            system_message = Template(self.llm_cfg["sp"]).render(**params)
            user_message = Template(self.llm_cfg["up"]).render(**params)
            messages = []
            messages = self.set_system_message(messages, system_message)
            messages = self.set_user_message(messages, user_message)

            try:
                chat_response = self.chat(messages)
                original_texts = json.loads(chat_response)
                if (
                    isinstance(original_texts, list)
                    and len(original_texts) == len(result.translated_texts)
                    and "".join(original_texts) == result.original_text
                ):
                    success = True
                    result.original_texts = original_texts
            except Exception as e:
                logger.error(f"Analyse error: {e}")
                retry_count += 1
        if not success:
            logger.error(f"Failed to analyse batch after {max_retries} retries. ")

    def exec(self, original_text: str, translated_texts: list[str]) -> DivResult:
        result = DivResult(
            original_text=original_text,
            translated_texts=translated_texts,
            original_texts=[],
        )
        self.divide(result)
        return result
