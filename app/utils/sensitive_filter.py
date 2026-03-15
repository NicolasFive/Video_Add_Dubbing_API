"""
敏感词过滤和处理模块
用于检测、过滤和还原文本中的违禁词
"""

import re
import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# 违禁词列表（可扩展）
# 你可以添加自己的违禁词
SENSITIVE_WORDS = [
    # 示例违禁词，请根据实际需求修改
    r"\b(forbidden|banned|illegal)\b",  # 英文例子
    r"(禁用词|违禁|黑名单)",  # 中文例子
]


class SensitiveFilter:
    """敏感词过滤器"""

    def __init__(
        self,
        sensitive_words: List[str] = None,
        placeholder_template: str = "[SENSITIVE_WORD_{idx}]",
    ):
        """
        初始化敏感词过滤器

        Args:
            sensitive_words: 违禁词列表，若为None则使用默认列表
        """
        self.sensitive_words = sensitive_words or SENSITIVE_WORDS
        self.placeholder_template = placeholder_template
        self.sensitive_replacements = {}

    @staticmethod
    def update_sensitive_words(words: List[str]) -> None:
        """
        更新全局违禁词列表

        Args:
            words: 新的违禁词列表
        """
        global SENSITIVE_WORDS
        SENSITIVE_WORDS = words

    def has_sensitive_word(self, text: str) -> bool:
        """
        检测文本中是否包含违禁词

        Args:
            text: 待检测的文本

        Returns:
            True如果包含违禁词，否则False
        """
        for pattern in self.sensitive_words:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def filter_and_mark(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        用占位符替换敏感词，保存映射关系以便后续恢复

        Args:
            text: 原始文本

        Returns:
            (处理后的文本, 替换映射字典)
        """
        filtered_text = text
        replacements = {}
        placeholder_idx = 0

        for pattern in self.sensitive_words:
            matches = re.finditer(pattern, filtered_text, re.IGNORECASE)
            for match in matches:
                placeholder = self.placeholder_template.format(idx=placeholder_idx)
                original_word = match.group(0)
                filtered_text = filtered_text.replace(original_word, placeholder, 1)
                replacements[placeholder] = original_word
                placeholder_idx += 1

        if replacements:
            logger.info(
                f"Detected and replaced {len(replacements)} sensitive word(s) in text"
            )
            logger.debug(f"Sensitive word replacements: {replacements}")

        return filtered_text, replacements

    def restore_sensitive_words(self, text: str, replacements: Dict[str, str]) -> str:
        """
        恢复被替换的敏感词

        Args:
            text: 包含占位符的文本
            replacements: 替换映射字典

        Returns:
            恢复后的文本
        """
        restored_text = text
        for placeholder, original_word in replacements.items():
            restored_text = restored_text.replace(placeholder, original_word)
        return restored_text

    def process_texts(self, texts: List[str]) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        批量处理文本列表，替换所有敏感词

        Args:
            texts: 文本列表

        Returns:
            (处理后的文本列表, 替换映射列表)
        """
        processed_texts = []
        all_replacements = []

        for text in texts:
            has_sensitive = self.has_sensitive_word(text)
            if has_sensitive:
                filtered_text, replacements = self.filter_and_mark(text)
                processed_texts.append(filtered_text)
                all_replacements.append(replacements)
                logger.warning(f"Text contains sensitive words: {text[:50]}...")
            else:
                processed_texts.append(text)
                all_replacements.append({})

        return processed_texts, all_replacements

    def restore_texts(
        self, texts: List[str], replacements_list: List[Dict[str, str]]
    ) -> List[str]:
        """
        批量恢复文本中的敏感词

        Args:
            texts: 文本列表
            replacements_list: 对应的替换映射列表

        Returns:
            恢复后的文本列表
        """
        restored_texts = []
        for text, replacements in zip(texts, replacements_list):
            restored_text = self.restore_sensitive_words(text, replacements)
            restored_texts.append(restored_text)
        return restored_texts
