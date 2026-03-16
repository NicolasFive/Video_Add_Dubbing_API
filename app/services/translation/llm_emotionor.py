from app.models.domain import ReducerData
from app.services.translation.llm_base import LLMBase
from jinja2 import Template
import json
import logging

logger = logging.getLogger(__name__)



class LLMEmotionor(LLMBase):

    def __init__(self):
        super().__init__("app/core/emotion_llm_cfg.json")

    def analyse(self, data_list: list[str], max_retries=3) -> list[str]:
        batch_size = 20
        reduced_texts = []
        reduce_messages = []

        for i in range(0, len(data_list), batch_size):
            batch = data_list[i : i + batch_size]
            retry_count = 0
            success = False
            current_result = None

            while retry_count <= max_retries and not success:
                params = {"data": json.dumps(batch, ensure_ascii=False)}
                system_message = Template(self.llm_cfg["sp"]).render(**params)
                user_message = Template(self.llm_cfg["up"]).render(**params)
                messages = reduce_messages
                messages = self.set_system_message(messages, system_message)
                messages = self.set_user_message(messages, user_message)
                try:
                    result = self.chat(messages)
                    result_json = json.loads(result)
                    if len(result_json) == len(batch):
                        current_result = result_json
                        success = True
                    else:
                        retry_count += 1
                        logger.warning(
                            f"Batch size mismatch: expected {len(batch)}, got {len(result_json)}. Retry {retry_count}/{max_retries}"
                        )
                        logger.debug(
                            f"Batch content: {json.dumps(batch, ensure_ascii=False)}"
                        )
                        logger.debug(
                            f"Result content: {json.dumps(result_json, ensure_ascii=False)}"
                        )
                except Exception as e:
                    logger.error(f"Analyse error: {e}")
                    retry_count += 1

            if success:
                reduced_texts.extend(current_result)
            else:
                # 最终失败，返回空
                logger.error(
                    f"Failed to analyse batch after {max_retries} retries. Falling back to original."
                )
                reduced_texts.extend(["" for d in batch])

        return reduced_texts
    def exec(self, data_list:list[str]) -> list[str]:
        self.emotion_texts = self.analyse(data_list)
        return self.emotion_texts