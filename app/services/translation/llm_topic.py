from unittest import result

from app.services.translation.llm_base import LLMBase
from jinja2 import Template
import json
import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class StyleContext(BaseModel):
    start: int
    tags: list


class TopicContext(BaseModel):
    topic: str
    styles: list[StyleContext]


class TranslationContext(BaseModel):
    start: int
    end: int
    topic: str
    styles: str


class LLMTopicor(LLMBase):

    def __init__(self):
        super().__init__("app/core/topic_llm_cfg.json")

    def analyse(self, texts: list[str], max_retries=3) -> TopicContext:
        batch_size = 100
        result = TopicContext(topic="", styles=[])
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            retry_count = 0
            success = False
            while retry_count <= max_retries and not success:
                params = {"data": json.dumps(batch_texts, ensure_ascii=False)}
                system_message = Template(self.llm_cfg["sp"]).render(**params)
                user_message = Template(self.llm_cfg["up"]).render(**params)
                messages = []
                messages = self.set_system_message(messages, system_message)
                messages = self.set_user_message(messages, user_message)

                try:
                    chat_response = self.chat(messages)
                    topic_contexts = json.loads(chat_response)
                    topic_contexts = (
                        topic_contexts if isinstance(topic_contexts, dict) else {}
                    )
                    result.topic = topic_contexts.get("core_theme", "")
                    result.styles.extend(
                        [
                            StyleContext(
                                start=style.get("start_index", 0) + i,
                                tags=style.get("style_tags", []),
                            )
                            for style in topic_contexts.get("style_evolution", [])
                        ]
                    )
                    success = True
                    logger.info(f"Analyse batch {i+batch_size}/{len(texts)} success.")
                except Exception as e:
                    logger.error(f"Analyse error: {e}")
                    retry_count += 1
            if not success:
                logger.error(f"Failed to analyse batch after {max_retries} retries. ")
        return result

    def exec(self, texts: list[str]) -> list[TranslationContext]:
        # 1. 调用大模型分析文本，获取主题和风格演变信息
        topic_context = self.analyse(texts)
        # 2. 根据分析结果生成翻译上下文信息（主题、风格标签等），供翻译模型使用
        translation_contexts = self.parse_to_translation_contexts(topic_context, texts)
        # 3. 校准上下文信息的边界完整性
        translation_contexts = self.validate_contexts(translation_contexts, texts)

        return translation_contexts

    def parse_to_translation_contexts(
        self, topic_context: TopicContext, texts: list[str]
    ) -> list[TranslationContext]:
        result = []
        tags_dict = self.llm_cfg["tags_dict"]
        for i, style in enumerate(topic_context.styles):
            start = style.start
            end = (
                topic_context.styles[i + 1].start
                if i + 1 < len(topic_context.styles)
                else len(texts)
            )
            prompts = []
            for dict in tags_dict:
                tag = dict["tag"]
                if tag in style.tags:
                    # prompt = f"{tag}（{dict['description']}），常用词汇包括：{', '.join(dict['keywords'])}"
                    prompt = f"{tag}（{dict['description']}）"
                    prompts.append(prompt)
            styles_str = "\n".join(prompts) if prompts else "无"
            result.append(
                TranslationContext(
                    topic=topic_context.topic, styles=styles_str, start=start, end=end
                )
            )
        return result

    def validate_contexts(
        self, contexts: list[TranslationContext], texts: list[str]
    ) -> list[TranslationContext]:
        # 原则1：第一个上下文的起始位置必须为0
        # 原则2：最后一个上下文的结束位置必须为文本长度
        # 原则3：相邻上下文之间的边界必须连续（即前一个上下文的结束位置应等于后一个上下文的起始位置）
        # 原则4：如果存在边界不连续的情况，优先调整前一个上下文的结束位置以保持连续性
        # 原则5：如果调整前一个上下文的结束位置导致其长度为0或负数，则调整后一个上下文的起始位置
        # 原则6：如果调整后一个上下文的起始位置导致其长度为0或负数，则删除该上下文
        # 原则7：确保调整后的上下文列表仍然覆盖整个文本范围且无重叠
        if not contexts:
            return contexts

        text_len = len(texts)

        # 原则1：调整第一个上下文起始位置为0
        contexts[0].start = 0

        # 原则2：调整最后一个上下文结束位置为文本长度
        contexts[-1].end = text_len

        # 原则3-7：处理相邻上下文边界连续性
        i = 0
        while i < len(contexts) - 1:
            current = contexts[i]
            next_ctx = contexts[i + 1]

            if current.end != next_ctx.start:
                # 原则4：优先调整前一个上下文的结束位置
                current.end = next_ctx.start

                # 原则5：如果调整导致长度为0或负数，调整后一个上下文的起始位置
                if current.end <= current.start:
                    current.end = current.start
                    next_ctx.start = current.start

                    # 原则6：如果后一个上下文长度为0或负数，删除它
                    if next_ctx.end <= next_ctx.start:
                        contexts.pop(i + 1)
                        continue

            i += 1

        return contexts
