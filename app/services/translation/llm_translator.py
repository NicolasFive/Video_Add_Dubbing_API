from app.services.translation.llm_base import LLMBase
from app.utils.sensitive_filter import SensitiveFilter
from jinja2 import Template
import json
import logging

logger = logging.getLogger(__name__)


class LLMTranslator(LLMBase):
    def __init__(self):
        super().__init__("app/core/translate_llm_cfg.json")
        sensitive_words = [
            "suck it",
            # "nigger",
            # "nigga",
            # "faggot",
            # "fag",
            # "dyke",
            # "kike",
            # "spic",
            # "chink",
            # "gook",
            # "paki",
            # "cunt",
            # "fuck",
            # "fucker",
            # "fucking",
            # "motherfucker",
            # "shit",
            # "asshole",
            # "bitch",
            # "bastard",
            # "damn",
            # "hell",
            # "rape",
            # "rapist",
            # "pedophile",
            # "incest",
            # "porn",
            # "suicide",
            # "kill yourself",
            # "self-harm",
            # "cutting",
            # "overdose",
            # "bomb",
            # "terrorist",
            # "isis",
            # "al-qaeda",
            # "hitler",
            # "nazism",
            # "white supremacy",
            # "slur",
            # "hate speech",
            # "threat",
            # "violence",
            # "gore",
            # "torture",
            # "abuse",
            # "harassment",
            # "stalking",
            # "doxxing",
            # "swatting",
        ]
        self.sensitive_filter = SensitiveFilter(
            sensitive_words=sensitive_words, placeholder_template="!!!"
        )

    def chat(self, messages: list):
        return super().chat(messages)

    def batch_process(self, texts: list[str], max_retries=3, batch_size = 20) -> list[str]:
        translated_texts = []
        translate_messages = []

        # 第一步：处理违禁词，用占位符替换
        processed_texts, replacements_list = self.sensitive_filter.process_texts(texts)

        for i in range(0, len(processed_texts), batch_size):
            batch = processed_texts[i : i + batch_size]
            batch_replacements = replacements_list[i : i + batch_size]
            retry_count = 0
            success = False
            current_result = None

            while retry_count < max_retries and not success:
                params = {"text": batch}
                system_message = Template(self.llm_cfg["sp"]).render(**params)
                user_message = Template(self.llm_cfg["up"]).render(**params)
                messages = translate_messages
                messages = self.set_system_message(messages, system_message)
                messages = self.set_user_message(messages, user_message)
                try:
                    result = self.chat(messages)
                    result_json = json.loads(result)
                    if len(result_json) == len(
                        batch
                    ):  # 注意：应比较 len(batch)，而非 batch_size（末尾批次可能不足）
                        current_result = result_json
                        success = True
                    elif batch_size == 1: # batch_size==1 时意味着是逐行处理模式
                        current_result = ["".join(result_json)]
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
                    logger.error(f"Translation error: {e}")
                    retry_count += 1

            if success:
                translated_texts.extend(current_result)
                logger.info(
                    f"Translate texts of {len(translated_texts)}/{len(texts)} successfully."
                )
            else:
                # 最终失败，使用逐行处理 (Line-by-Line)
                logger.error(
                    f"Failed to translate batch after {max_retries} retries. Falling back to line-by-line processing for this batch."
                )
                line_results = self.line_by_line(batch)
                translated_texts.extend(line_results)

        return translated_texts
    
    
    def line_by_line(self, texts: list[str]) -> list[str]:
        translated_texts = []
        for text in texts:
            results = self.batch_process([text], batch_size=1)  # 逐行处理，batch_size=1
            translated_texts.extend(results)
        return translated_texts

    def exec(self, texts: list[str]) -> list[str]:
        self.translated_texts = self.batch_process(texts)
        return self.translated_texts
