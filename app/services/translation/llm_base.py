from abc import ABC, abstractmethod
from openai import OpenAI
from app.core.config import settings
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class LLMBase(ABC):
    """LLM处理基类，提供通用的OpenAI客户端和消息管理功能"""

    def __init__(self, cfg_file_path: str):
        """
        初始化LLM基类

        Args:
            cfg_file_path: 配置文件路径（相对于项目根目录）
        """
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL
        )
        llm_cfg_filepath = Path(cfg_file_path).resolve()
        with open(llm_cfg_filepath, "r", encoding="utf-8") as f:
            self.llm_cfg = json.load(f)

    def chat(self, messages: list) -> str:
        """
        调用OpenAI API进行对话

        Args:
            messages: 消息列表

        Returns:
            模型返回的文本内容
        """
        completion = self.client.chat.completions.create(
            # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            model="qwen-plus",
            messages=messages,
        )
        logger.debug(f"OpenAI Response: {completion.model_dump_json()}")
        return completion.choices[0].message.content

    @abstractmethod
    def exec(self, *args, **kwargs):
        """
        执行LLM处理的抽象方法，由子类实现

        子类应该实现具体的处理逻辑（如翻译、缩减等）
        """
        pass

    def set_system_message(self, messages: list, system_message: str) -> list:
        """
        设置或替换系统消息

        Args:
            messages: 消息列表
            system_message: 系统消息内容

        Returns:
            更新后的消息列表
        """
        handled_messages = [m for m in messages if m["role"] != "system"]
        handled_messages.insert(0, {"role": "system", "content": system_message})
        return handled_messages

    def set_user_message(self, messages: list, user_message: str) -> list:
        """
        设置或替换最后的用户消息

        Args:
            messages: 消息列表
            user_message: 用户消息内容

        Returns:
            更新后的消息列表
        """
        handled_messages = [m for m in messages if m["role"] != "user"]
        handled_messages.append({"role": "user", "content": user_message})
        return handled_messages

    def add_user_message(self, messages: list, user_message: str) -> list:
        """
        添加用户消息到消息列表末尾

        Args:
            messages: 消息列表
            user_message: 用户消息内容

        Returns:
            更新后的消息列表
        """
        messages.append({"role": "user", "content": user_message})
        return messages

    def add_assistant_message(self, messages: list, assistant_message: str) -> list:
        """
        添加助手消息到消息列表末尾

        Args:
            messages: 消息列表
            assistant_message: 助手消息内容

        Returns:
            更新后的消息列表
        """
        messages.append({"role": "assistant", "content": assistant_message})
        return messages
