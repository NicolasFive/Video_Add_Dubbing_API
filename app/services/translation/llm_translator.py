from app.services.translation.llm_base import LLMBase
from app.services.translation.llm_topic import LLMTopicor, TranslationContext
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
        self.topicor = LLMTopicor()

    def chat(self, messages: list):
        return super().chat(messages)

    def batch_process(
        self,
        texts: list[str],
        contexts: list[TranslationContext],
        max_retries=3,
        batch_size=20,
    ) -> list[str]:
        result = []

        # 1. 处理违禁词，用占位符替换
        processed_texts, _ = self.sensitive_filter.process_texts(texts)

        # 2. 按照上下文信息分批处理文本
        for context in contexts:
            start = context.start
            end = context.end
            same_context_texts = processed_texts[start:end]
            # 3. 相同上下文信息的文本进一步分批处理，控制每批文本数量，避免一次性处理过多文本导致模型响应过慢或失败
            for i in range(0, len(same_context_texts), batch_size):
                batch = same_context_texts[i : i + batch_size]

                retry_count = 0
                success = False

                while retry_count < max_retries and not success:
                    params = {"text": batch}
                    system_message = Template(self.llm_cfg["sp"]).render(**params)
                    user_message = Template(self.llm_cfg["up"]).render(**params)
                    messages = []
                    messages = self.set_system_message(messages, system_message)
                    messages = self.set_user_message(messages, user_message)
                    try:
                        chat_response = self.chat(messages)
                        translate_texts = json.loads(chat_response)
                        if len(translate_texts) == len(
                            batch
                        ):  # 注意：应比较 len(batch)，而非 batch_size（末尾批次可能不足）
                            result.extend(translate_texts)
                            success = True
                        elif batch_size == 1:  # batch_size==1 时意味着是逐行处理模式
                            result.extend(["".join(translate_texts)])
                            success = True
                        else:
                            retry_count += 1
                            logger.warning(
                                f"Batch size mismatch: expected {len(batch)}, got {len(translate_texts)}. Retry {retry_count}/{max_retries}"
                            )
                    except Exception as e:
                        logger.error(f"Translation error: {e}")
                        retry_count += 1

                if success:
                    logger.info(
                        f"Translate texts of {len(result)}/{len(texts)} successfully."
                    )
                else:
                    # 最终失败，使用逐行处理 (Line-by-Line)
                    logger.error(
                        f"Failed to translate batch after {max_retries} retries. Falling back to line-by-line processing for this batch."
                    )
                    line_results = self.line_by_line(batch, context)
                    result.extend(line_results)

        return result

    def line_by_line(self, texts: list[str], context: TranslationContext) -> list[str]:
        result = []
        adjust_context = TranslationContext(
            start=0,
            end=len(texts),
            topic=context.topic,
            styles=context.styles,
        )
        for text in texts:
            results = self.batch_process(
                [text], [adjust_context], batch_size=1
            )  # 逐行处理，batch_size=1
            result.extend(results)
        return result

    def exec(self, texts: list[str]) -> list[str]:
        # 1. 分析文本主题和风格
        translate_contexts = self.topicor.exec(texts)
        # 2. 批量翻译文本
        self.result = self.batch_process(texts, translate_contexts)
        return self.result
