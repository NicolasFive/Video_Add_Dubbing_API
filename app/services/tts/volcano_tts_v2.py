from pathlib import Path
from app.core.config import settings
from app.core.exceptions import FileProcessingError
from app.models.domain import SubtitleLine
from app.services.translation.llm_reducer import LLMReducer
from app.utils.cmd_runner import CmdRunner
import asyncio
from app.utils.audio_utils import get_audio_duration
import logging
from app.services.tts.volcengine.binary_v2 import run_volcengine
import math
from typing import Optional
from pydantic import BaseModel
from app.services.tts.volcano_tts import get_volcengine_params

logger = logging.getLogger(__name__)


class VolcanoTTSService:
    def synthesize(
        self,
        text: str,
        expect_duration_ms: Optional[int],
        output_path: Path,
        voice_type: str = "zh_female_xiaohe_uranus_bigtts",  # 音色列表 https://www.volcengine.com/docs/6561/1257544?lang=zh
        emotion: Optional[
            str
        ] = None,  # 情感列表 https://www.volcengine.com/docs/6561/1257544?lang=zh
        context_texts: Optional[list] = None,  # 语音合成的辅助信息
        section_id: Optional[str] = None,  # 章节ID，用于上下文关联

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
            context_texts=context_texts,
            section_id=section_id,
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
        context_texts: Optional[list] = None,
        section_id: Optional[str] = None,
        retry:bool=True,
    )->None:
        asyncio.run(
            run_volcengine(
                appid=settings.VOLCANO_TTS_V2_APPID,
                access_token=settings.VOLCANO_TTS_V2_ACCESS_TOKEN,
                voice_type=voice_type,
                text=text,
                speed_ratio=speed_ratio,
                loudness_ratio=loudness_ratio,
                encoding="wav",
                output_path=str(output_path),
                emotion=emotion,
                context_texts=context_texts,
                section_id=section_id,
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
                context_texts=context_texts,
                section_id=section_id,
                retry=False
            )


