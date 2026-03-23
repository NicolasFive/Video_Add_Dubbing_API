from pathlib import Path
from app.core.config import settings
from app.core.exceptions import FileProcessingError
from app.models.domain import SubtitleLine
from app.services.translation.llm_reducer import LLMReducer
from app.utils.cmd_runner import CmdRunner
import asyncio
import json
import logging
from app.services.tts.volcengine.binary import run_volcengine
import math
from typing import Optional
from pydantic import BaseModel
from app.utils.audio_utils import get_audio_duration
import re

logger = logging.getLogger(__name__)


class VolcanoTTSService:
    def synthesize(
        self,
        text: str,
        expect_duration_ms: Optional[int],
        output_path: Path,
        voice_type: str = "zh_female_cancan_mars_bigtts",  # 音色列表 https://www.volcengine.com/docs/6561/1257544?lang=zh
        emotion: Optional[
            str
        ] = None,  # 情感列表 https://www.volcengine.com/docs/6561/1257544?lang=zh
    ) -> None:
        """生成单段音频"""
        params = get_volcengine_params(
            text, expect_duration_ms / 1000 if expect_duration_ms else None
        )
        print(
            f"Calculated Volcengine TTS params: speed_ratio={params.speed_ratio}, loudness_ratio={params.loudness_ratio}"
        )
        # 限制 speed_ratio 不低于 1.0
        params.speed_ratio = max(1.0, params.speed_ratio)
        self.fallback_exec(
            voice_type=voice_type,
            text=text,
            speed_ratio=params.speed_ratio,
            loudness_ratio=params.loudness_ratio,
            emotion=emotion,
            output_path=output_path,
            expect_duration_ms=expect_duration_ms,
        )

    def fallback_exec(
        self,
        voice_type: str,
        text: str,
        speed_ratio: float,
        loudness_ratio: float,
        output_path: Path,
        emotion: Optional[str],
        expect_duration_ms: Optional[int],
        retry:bool=True,
    )->None:
        asyncio.run(
            run_volcengine(
                appid=settings.VOLCANO_TTS_V1_APPID,
                access_token=settings.VOLCANO_TTS_V1_ACCESS_TOKEN,
                voice_type=voice_type,
                text=text,
                speed_ratio=speed_ratio,
                loudness_ratio=loudness_ratio,
                encoding="wav",
                output_path=str(output_path),
                emotion=emotion,
            )
        )
        if not output_path.exists():
            raise Exception("TTS generation failed")

        # 1. 获取生成的音频时长
        actual_duration_sec = get_audio_duration(output_path)
        actual_duration_ms = round(actual_duration_sec * 1000)

        # 2. 如果没有期望时长或实际时长已经接近目标时长，则直接返回
        if not expect_duration_ms:
            return
        # 3. 如果实际时长已经在目标时长的合理范围内（例如+500ms），则直接返回（如果实际时长小于目标时长也不处理，直接返回）
        if actual_duration_ms < (expect_duration_ms + 500):
            return
        # 4. 调整音频播放速率以匹配目标时长

        # 4.1 计算加速速率
        # speed_ratio = 实际时长 / 目标时长
        # 例：实际 1.2s，目标 1.0s，speed_ratio = 1.2（需要加速 1.2 倍）
        adjust_ratio = actual_duration_ms / expect_duration_ms
        adjust_ratio = (
            math.ceil(adjust_ratio * 100) / 100
        )  # 保留两位小数，向上取整，避免略微不足导致音频过短
        logger.info(
            f"Audio speed adjustment: actual={actual_duration_ms:.3f}ms, "
            f"target={expect_duration_ms:.3f}ms, speed_ratio={adjust_ratio:.2f}"
        )

        # 4.2 如果加速速率大于1.2或小于0.7，则重新调用TTS生成
        if (adjust_ratio > 1.2 or adjust_ratio < 0.8) and retry:
            logger.info(
                f"Speed ratio {adjust_ratio:.2f} is out of acceptable range, regenerating TTS with adjusted parameters"
            )
            # 重新计算参数speed_ratio
            new_speed_ratio = speed_ratio * adjust_ratio
            if adjust_ratio<1.0:
                new_speed_ratio += 0.1
            new_speed_ratio = max(0.5, min(2.0, new_speed_ratio))
            return self.fallback_exec(
                voice_type=voice_type,
                text=text,
                speed_ratio=new_speed_ratio,
                loudness_ratio=loudness_ratio,
                emotion=emotion,
                output_path=output_path,
                expect_duration_ms=expect_duration_ms,
                retry=False
            )




class VolcengineParams(BaseModel):
    speed_ratio: float
    loudness_ratio: float


def get_volcengine_params(
    text: str,
    target_duration_sec: Optional[float] = None,
    # 中文基准：约 4.8 字/秒 (不含标点停顿)
    base_cps_zh: float = 4.8,
    # 英文基准：约 2.5 词/秒
    base_wps_en: float = 2.5,
    # 标点停顿估算 (秒) - 可根据实际 TTS 引擎表现微调
    pause_comma: float = 0.25,   # 逗号、顿号
    pause_period: float = 0.45,  # 句号、问号、感叹号
    pause_other: float = 0.15,   # 分号、冒号等
) -> VolcengineParams:
    if target_duration_sec is None or target_duration_sec <= 0:
        return VolcengineParams(speed_ratio=1.0, loudness_ratio=1.0)

    # --- 1. 统计字符与单词 ---
    
    # 中文字符
    zh_chars = re.findall(r"[\u4e00-\u9fff]", text)
    zh_count = len(zh_chars)

    # 英文单词
    en_words = re.findall(r"[a-zA-Z]+", text)
    en_count = len(en_words)

    if zh_count == 0 and en_count == 0:
        return VolcengineParams(speed_ratio=1.0, loudness_ratio=1.0)

    # --- 2. 统计标点符号并估算停顿时长 ---
    
    # 定义标点正则
    commas = len(re.findall(r"[，,、]", text))      # 短停顿
    periods = len(re.findall(r"[。.?!！]", text))   # 长停顿
    others = len(re.findall(r"[；:…]", text))       # 中等停顿
    
    # 计算标点总耗时
    punctuation_duration = (
        commas * pause_comma +
        periods * pause_period +
        others * pause_other
    )

    # --- 3. 计算总预估时长 ---
    
    estimated_zh_duration = zh_count / base_cps_zh
    estimated_en_duration = en_count / base_wps_en
    
    # 总时长 = 读音时长 + 标点停顿时长
    estimated_duration_sec = estimated_zh_duration + estimated_en_duration + punctuation_duration

    # --- 4. 计算速度比率 ---
    if estimated_duration_sec == 0:
        speed_ratio = 1.0
    else:
        # 目标时长越短，需要的速度比率越大
        speed_ratio = estimated_duration_sec / target_duration_sec

    # 限制速度范围 (0.1x ~ 2.0x)
    speed_ratio = round(max(0.1, min(2.0, speed_ratio)), 1)

    # --- 5. 动态调整音量 ---
    loudness_ratio = 1.0
    loudness_offset = (speed_ratio - 1.0) * 0.5
    loudness_ratio += round(loudness_offset, 1)
    loudness_ratio = max(0.5, min(2.0, loudness_ratio))

    return VolcengineParams(speed_ratio=speed_ratio, loudness_ratio=loudness_ratio)

