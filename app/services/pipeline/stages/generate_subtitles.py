from __future__ import annotations

from app.models.domain import ProcessingContext, SelfCheckItem
from app.services.subtitle.generator import SubtitleGenerator
import re
from app.services.pipeline.base import BasePipelineStage
from pathlib import Path


class RuleBasedGenerateSubtitlesStage(BasePipelineStage):
    def __init__(self):
        self.sub_gen = SubtitleGenerator()

    def run(self, ctx: ProcessingContext) -> None:
        if ctx.input_video_path is None:
            return
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        subtitles = (
            ctx.optimized_subtitles if ctx.optimized_subtitles else ctx.subtitles
        )
        self.sub_gen.generate_srt(
            subtitles,
            str(srt_path),
            ctx.input_video_width,
            ctx.subtitle_font_size,
        )
        ctx.final_subtitle_path = str(srt_path)

    def restore(self, ctx: ProcessingContext) -> bool:
        pass

    def logfile_name(self) -> str:
        pass
    
    def save_log(self, ctx: ProcessingContext) -> None:
        pass
    
    def read_log(self, ctx: ProcessingContext) -> str:
        log_name = self.logfile_name()
        return super()._read_log(ctx, log_name=log_name)
    
    def get_data(self, ctx) -> str:
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        if srt_path.exists():
            with open(srt_path, "r", encoding="utf-8") as f:
                return f.read()
        return "None"

    def set_data(self, ctx, data: str):
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        data = data.replace("\r", "")  # 将转义的换行符转换为实际的换行
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(data)

    def self_check(self, ctx) -> list[SelfCheckItem]:
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        subtitles = (
            ctx.optimized_subtitles if ctx.optimized_subtitles else ctx.subtitles
        )
        # 解析srt文件，检查是否存在没有双语字幕的条目，提示用户确认。
        check_results = []
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
            entities = re.split(r"\n{2,}", content.strip())  # 按照连续的空行分割成条目
            start_index = 0

            for i, entity in enumerate(entities):
                lines = entity.splitlines()
                # 防止下标越界
                if start_index >= len(subtitles):
                    original_text = ""
                else:
                    subtitle = subtitles[start_index]
                    original_text = subtitle.original_text.strip()
                is_match = False
                for line in lines:
                    line = line.strip()
                    if original_text.endswith(line):
                        start_index += 1
                        is_match = True
                        break
                    if line in original_text:
                        is_match = True
                        break
                if not is_match:
                    if i > 0 and (not check_results or check_results[-1].index != i):
                        check_results.append(
                            SelfCheckItem(
                                index=i,
                                check_point="content",
                                issue=f"可能需要裁剪部分英文字幕到下一段。",
                                warning_content=f"",
                                confirm_content=entities[i - 1],
                            ),
                        )
                    check_results.append(
                        SelfCheckItem(
                            index=i + 1,
                            check_point="content",
                            issue=f"检测到第{i+1}条字幕内容不包含双语，请手动调整。",
                            warning_content=f"{entity}",
                            confirm_content=entity,
                        ),
                    )
        return check_results

    def check_confirm(self, ctx, data: list[SelfCheckItem]):
        srt_path = Path(ctx.work_dir) / "subtitles.srt"
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
            entities = re.split(r"\n{2,}", content.strip())  # 按照连续的空行分割成条目
            for item in data:
                entity = entities[item.index - 1]
                if entity.strip().startswith(str(item.index)):
                    entities[item.index - 1] = item.confirm_content
            new_content = "\n\n".join(entities)
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write(new_content)
