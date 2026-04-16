from app.models.domain import ReducerData
from app.services.translation.llm_base import LLMBase
from jinja2 import Template
import json
import logging

logger = logging.getLogger(__name__)



class LLMReducer(LLMBase):

    def __init__(self):
        super().__init__("app/core/reduce_llm_cfg.json")

    def reduce(self, data: ReducerData, max_retries=3) -> str:
        retry_count = 0
        success = False
        while retry_count <= max_retries and not success:
            params = {"data": data.text}
            system_message = Template(self.llm_cfg["sp"]).render(**params)
            user_message = Template(self.llm_cfg["up"]).render(**params)
            messages = []
            messages = self.set_system_message(messages, system_message)
            messages = self.set_user_message(messages, user_message)
            try:
                result = self.chat(messages)
                if result.count("\n") == data.text.count("\n"):
                    data.reduced_text = result.strip()
                    success = True
                else:
                    retry_count += 1
                    logger.warning(f"Line count mismatch: expected {data.text.count('\n')}, got {result.count('\n')}. Retry {retry_count}/{max_retries}")
            except Exception as e:
                logger.error(f"Reduce error: {e}")
                retry_count += 1

        if not success:
            # 最终失败，回退到原文
            data.reduced_text = data.text
            logger.error(
                f"Failed to reduce after {max_retries} retries. Falling back to original."
            )
        return data.reduced_text
    
    def exec(self, data:ReducerData) -> str:
        self.reduced_text = self.reduce(data)
        return self.reduced_text