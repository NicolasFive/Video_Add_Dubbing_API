import logging
from typing import Tuple
from app.models.domain import DurationRating

logger = logging.getLogger(__name__)


class SpeedRatioChecker:
    def check(self, speed_ratio: float) -> Tuple[DurationRating, float]:
        """
        预检查计算字幕的 speed_ratio 是否存在以下问题：
        1. 绝对速率过快：speed_ratio > uppper_threshold（如 1.3），可能导致配音听起来不自然，语速过快。
        2. 绝对速率过慢：speed_ratio < lower_threshold（如 0.8），可能导致配音听起来拖沓，语速过慢。
        """
        uppper_threshold = 1.3
        lower_threshold = 0.8

        rating = None
        upper_target_ratio = 2.0

        # 1. 判断绝对速率是否超过 uppper_threshold，如果超过则视为过长
        if speed_ratio > uppper_threshold:
            rating = DurationRating.TOO_LONG
            # 目标：将 speed_ratio 降到不高于 uppper_threshold
            upper_target_ratio = uppper_threshold
        elif speed_ratio <= lower_threshold:
            rating = DurationRating.TOO_SHORT
        target_ratio = min(speed_ratio, upper_target_ratio)
        return (rating, target_ratio)
