from app.models.domain import ReducerData
from app.services.translation.llm_base import LLMBase
from jinja2 import Template
import json
import logging

logger = logging.getLogger(__name__)



class LLMReducer(LLMBase):

    def __init__(self):
        super().__init__("app/core/reduce_llm_cfg.json")

    def reduce(self, data_list: list[ReducerData], max_retries=3) -> list[str]:
        batch_size = 20
        reduced_texts = []
        reduce_messages = []

        for i in range(0, len(data_list), batch_size):
            batch = data_list[i : i + batch_size]
            retry_count = 0
            success = False
            current_result = None

            while retry_count <= max_retries and not success:
                data = [{"text": d.text, "target_length": d.target_length} for d in batch]
                params = {"data": json.dumps(data, ensure_ascii=False)}
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
                            f"Batch content: {json.dumps(data, ensure_ascii=False)}"
                        )
                        logger.debug(
                            f"Result content: {json.dumps(result_json, ensure_ascii=False)}"
                        )
                except Exception as e:
                    logger.error(f"Reduce error: {e}")
                    retry_count += 1

            if success:
                reduced_texts.extend(current_result)
                logger.info(
                    f"Reduced texts of {len(reduced_texts)}/{len(data_list)} successfully."
                )
            else:
                # 最终失败，回退到原文
                logger.error(
                    f"Failed to reduce batch after {max_retries} retries. Falling back to original."
                )
                reduced_texts.extend([d.text for d in batch])

        return reduced_texts
    def exec(self, data_list:list[ReducerData]) -> list[str]:
        self.reduced_texts = self.reduce(data_list)
        return self.reduced_texts