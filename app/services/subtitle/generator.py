import re
from app.models.domain import SubtitleLine
from app.utils.time_utils import ms_to_srt_time


class SubtitleGenerator:
    def __init__(self):
        # 分割标点
        self.punctuation = ".,;:,.:;、，。；：—"

    def generate_srt(
        self,
        subtitles: list[SubtitleLine],
        output_path: str,
        video_width: int,
        font_size: int,
        max_lines_on_screen: int = 1,
        original_text_on: bool = True,
    ):
        handled_subtitles = self._split_long_subtitles(
            subtitles, video_width, font_size, max_lines_on_screen,original_text_on
        )
        # handled_subtitles = subtitles
        with open(output_path, "w", encoding="utf-8") as f:
            for i, sub in enumerate(handled_subtitles):
                f.write(f"{i+1}\n")
                f.write(
                    f"{ms_to_srt_time(sub.start_ms)} --> {ms_to_srt_time(sub.end_ms)}\n"
                )
                if original_text_on:
                    f.write(f"{sub.translated_text}\n{sub.original_text}\n\n")
                else:
                    f.write(f"{sub.translated_text}\n\n")

    def _split_long_subtitles(
        self,
        subtitles: list[SubtitleLine],
        video_width: int,
        font_size: int,
        max_lines_on_screen: int = 1,
        original_text_on: bool = True,
    ) -> list[SubtitleLine]:
        """
        处理字幕列表，将过长的 text 拆分为多行，避免遮挡画面。
        返回新的 SubtitleLine 列表。

        :param subtitles: 原始字幕对象列表
        :param video_width: 视频宽度 (像素)
        :param font_size: 字体大小 (像素)
        :param max_lines_on_screen: 允许屏幕上同时显示的最大行数 (竖屏建议 1~2)
        :param original_text_on: 是否显示原文
        :return: 处理后的新 SubtitleLine 列表
        """

        # 1. 计算单行最大容纳字符数
        # 逻辑：可用宽度 (90%) / (字号 * 0.9)。中文通常接近正方形，留 10% 余量给字间距和边距
        safe_width = video_width * 0.9
        avg_char_width = font_size * 1.1
        max_chars_per_line = int(safe_width / avg_char_width*1.5) # 乘以1.5的系数是经验校正值

        # 保底设置，防止字号过大导致计算值过小
        if max_chars_per_line < 8:
            max_chars_per_line = 8

        print(
            f"[字幕优化] 视频宽:{video_width}, 字号:{font_size}, 单行限:{max_chars_per_line}字"
        )

        handled_subtitles = []

        for sub in subtitles:
            text_to_process = sub.translated_text
            # 1. 移除文本中的标点符号（感叹号、问号、百分号除外）
            cleaned_text = re.sub(r"[.,;,.;、，。；—…]", "  ", text_to_process)

            # 如果没有翻译文本，直接保留原对象
            if not cleaned_text:
                handled_subtitles.append(SubtitleLine(
                    start_ms=sub.start_ms,
                    end_ms=sub.end_ms,
                    original_text=sub.original_text,
                    translated_text=sub.translated_text,
                ))
                continue
            # 2. 逐行判断文本长度，超过限制则拆分
            lines_within_limit = []
            lines_split_num = []
            for line in cleaned_text.splitlines():
                # 判断该行长度是否超过限制，超过则拆分
                if len(line) > max_chars_per_line:
                    # 智能拆分文本
                    segments = self._smart_split_text(line, max_chars_per_line)
                    lines_within_limit.extend(segments)
                    lines_split_num.append(len(segments))
                else:
                    lines_within_limit.append(line)
                    lines_split_num.append(1)
            
            # 3. 将拆分后的行重新组合成新的 SubtitleLine 对象，时间轴均匀分布
            start_ms = sub.start_ms
            duration_ms = sub.end_ms - sub.start_ms
            arr = []
            for i in range(0, len(lines_within_limit), max_lines_on_screen):
                seg_text = "\n".join(lines_within_limit[i : i + max_lines_on_screen])
                # 计算结束时间
                if i + max_lines_on_screen >= len(lines_within_limit):
                    current_end = sub.end_ms  # 最后一段严格对齐原结束时间，防止误差
                else:
                    current_end = int(
                        start_ms + (duration_ms / len(cleaned_text)) * len(seg_text)
                    )
                arr.append(SubtitleLine(
                    start_ms=start_ms,
                    end_ms=current_end,
                    original_text="",
                    translated_text=seg_text,  # 使用拆分后的短句
                ))
                start_ms = current_end  # 下一段开始时间紧跟上一段结束时间
            
            # 4. 判断是否需要添加原文
            original_text_arr = sub.original_text.splitlines() if sub.original_text else []
            if original_text_on:
                idx=0
                for i, num in enumerate(lines_split_num):
                    arr[idx].original_text = original_text_arr[i] if i < len(original_text_arr) else ""
                    idx+=num
            handled_subtitles.extend(arr)
        return handled_subtitles

    def _smart_split_text(self, text: str, max_len: int) -> list[str]:
        """
        智能拆分文本，优先在标点符号或空格处断开。
        """
        segments = []
        remaining = text.strip()

        while len(remaining) > max_len:
            chunk = remaining[:max_len]
            next_chunk = remaining[max_len : max_len * 2]
            break_point = -1
            next_break_point = -1

            # 从后向前找最近的标点或空格
            # 搜索范围限制在 chunk 的后半部分 (max_len // 2 到 max_len)以及next_chunk的前半部分 (0 到 max_len // 2)，避免切得太碎
            search_start_index = max_len // 2
            next_search_end_index = min(max_len // 2, len(next_chunk))

            for i in range(max_len - 1, search_start_index - 1, -1):
                char = chunk[i]
                if char in self.punctuation or char == " ":
                    break_point = i
                    break

            for i in range(0, next_search_end_index - 1, 1):
                char = next_chunk[i]
                if char in self.punctuation or char == " ":
                    next_break_point = i
                    break

            if break_point != -1:
                # 在标点处切断
                segment = remaining[: break_point + 1].strip()
                remaining = remaining[break_point + 1 :].strip()
            elif next_break_point != -1:
                # 在下一个 chunk 的标点处切断
                segment = remaining[: max_len + next_break_point + 1].strip()
                remaining = remaining[max_len + next_break_point + 1 :].strip()
            else:
                # 没找到合适标点，强制在 max_len 处切断
                segment = remaining[:max_len].strip()
                remaining = remaining[max_len:].strip()

            if segment:
                segments.append(segment)

        if remaining:
            segments.append(remaining)

        return segments
