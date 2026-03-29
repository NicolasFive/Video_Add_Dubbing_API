from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Sequence

from app.core.exceptions import FileProcessingError
from app.utils.cmd_runner import CmdRunner


@dataclass(frozen=True)
class VideoDeleteSegment:
	start_ms: int
	end_ms: int


class FFmpegVideoCutter:
	def __init__(self, video_path: str):
		self.video_path = Path(video_path)
		if not self.video_path.exists():
			raise FileNotFoundError(f"Video file not found: {self.video_path}")

	def delete(self, segments: Sequence[VideoDeleteSegment | dict[str, Any]]) -> str:
		if not segments:
			return str(self.video_path)

		# 先将删除区间转成秒并合并重叠区间，后续只处理有序且不重叠的数据。
		delete_segments = self._normalize_delete_segments(segments)
		video_duration = self._get_video_duration()
		# 根据删除区间反推出需要保留的视频片段。
		keep_segments = self._build_keep_segments(delete_segments, video_duration)

		if not keep_segments:
			raise FileProcessingError("All video content would be removed by the provided segments")

		output_path = self._build_output_path()
		with TemporaryDirectory(prefix="video_cut_", dir=self.video_path.parent) as temp_dir:
			temp_dir_path = Path(temp_dir)
			part_paths = self._extract_keep_segments(keep_segments, temp_dir_path)
			concat_list_path = self._create_concat_list_file(part_paths, temp_dir_path)
			self._concat_segments(concat_list_path, output_path)

		if not output_path.exists():
			raise FileNotFoundError("Failed to generate output video after deleting segments")

		return str(output_path)

	def _normalize_delete_segments(
		self, segments: Sequence[VideoDeleteSegment | dict[str, Any]]
	) -> list[tuple[float, float]]:
		parsed_segments: list[tuple[float, float]] = []
		for segment in segments:
			start_value, end_value = self._extract_segment_values(segment)
			# 入参单位是毫秒，内部统一转换为秒，便于 ffmpeg 参数复用。
			start_seconds = self._parse_millisecond_value(start_value)
			end_seconds = self._parse_millisecond_value(end_value)
			if start_seconds < 0:
				raise ValueError("Segment start time must be greater than or equal to 0")
			if end_seconds <= start_seconds:
				raise ValueError("Segment end time must be greater than start time")
			parsed_segments.append((start_seconds, end_seconds))

		parsed_segments.sort(key=lambda item: item[0])

		merged_segments: list[tuple[float, float]] = []
		for start_seconds, end_seconds in parsed_segments:
			if not merged_segments:
				merged_segments.append((start_seconds, end_seconds))
				continue

			last_start, last_end = merged_segments[-1]
			# 相邻或重叠的删除区间直接合并，避免重复裁剪。
			if start_seconds <= last_end:
				merged_segments[-1] = (last_start, max(last_end, end_seconds))
				continue

			merged_segments.append((start_seconds, end_seconds))

		return merged_segments

	@staticmethod
	def _extract_segment_values(segment: VideoDeleteSegment | dict[str, Any]) -> tuple[Any, Any]:
		if isinstance(segment, VideoDeleteSegment):
			return segment.start_ms, segment.end_ms

		if isinstance(segment, dict):
			start_value = segment.get("start_ms", segment.get("start"))
			end_value = segment.get("end_ms", segment.get("end"))
			if start_value is None or end_value is None:
				raise ValueError("Each segment must contain start_ms/end_ms or start/end")
			return start_value, end_value

		raise TypeError("Each segment must be a VideoDeleteSegment or a dict")

	@staticmethod
	def _parse_millisecond_value(value: int | float) -> float:
		return float(value) / 1000

	def _get_video_duration(self) -> float:
		cmd = [
			"ffprobe",
			"-v",
			"error",
			"-show_entries",
			"format=duration",
			"-print_format",
			"json",
			str(self.video_path),
		]
		output = CmdRunner.run(cmd)

		try:
			result = json.loads(output)
			return float(result["format"]["duration"])
		except (ValueError, KeyError, json.JSONDecodeError) as exc:
			raise FileProcessingError(f"Failed to parse video duration: {exc}") from exc

	def _build_keep_segments(
		self, delete_segments: Sequence[tuple[float, float]], video_duration: float
	) -> list[tuple[float, float | None]]:
		keep_segments: list[tuple[float, float | None]] = []
		cursor = 0.0

		for start_seconds, end_seconds in delete_segments:
			if start_seconds >= video_duration:
				raise ValueError("Segment start time exceeds video duration")

			bounded_end = min(end_seconds, video_duration)
			# cursor 到下一个删除区间起点之间，都是需要保留的内容。
			if start_seconds > cursor:
				keep_segments.append((cursor, start_seconds))
			cursor = max(cursor, bounded_end)

		# 最后一个删除区间之后如果还有剩余，也要作为保留片段。
		if cursor < video_duration:
			keep_segments.append((cursor, None))

		return [segment for segment in keep_segments if segment[1] is None or segment[1] > segment[0]]

	def _extract_keep_segments(
		self, keep_segments: Sequence[tuple[float, float | None]], temp_dir: Path
	) -> list[Path]:
		part_paths: list[Path] = []
		for index, (start_seconds, end_seconds) in enumerate(keep_segments, start=1):
			part_path = temp_dir / f"part_{index:03d}{self.video_path.suffix}"
			# 使用 -c copy 做流复制，避免重新编码，速度快且不损画质。
			cmd = ["ffmpeg", "-y", "-i", str(self.video_path)]

			if start_seconds > 0:
				cmd.extend(["-ss", self._format_time(start_seconds)])
			if end_seconds is not None:
				cmd.extend(["-to", self._format_time(end_seconds)])

			# --- 重编码模式 (精确) ---
			# 使用 libx264 进行编码
			# CRF 18-23 是视觉无损范围，23 是默认值，速度快
			# preset veryfast 进一步加快编码速度
			cmd.extend([
				"-c:v", "libx264", 
				"-crf", "23", 
				"-preset", "veryfast",
				"-c:a", "aac",
				"-b:a", "128k" # 音频比特率，防止 AAC 编码时音质下降
			])
			cmd.append(str(part_path))
			CmdRunner.run(cmd)

			if not part_path.exists():
				raise FileNotFoundError(f"Failed to generate video segment: {part_path}")

			part_paths.append(part_path)

		return part_paths

	def _create_concat_list_file(self, part_paths: Sequence[Path], temp_dir: Path) -> Path:
		concat_list_path = temp_dir / "list.txt"
		# concat 模式要求按顺序提供每个分段文件路径。
		concat_lines = [f"file '{self._escape_concat_path(path)}'" for path in part_paths]
		concat_list_path.write_text("\n".join(concat_lines), encoding="utf-8")
		return concat_list_path

	def _concat_segments(self, concat_list_path: Path, output_path: Path) -> None:
		# 通过 concat 协议把保留片段无损拼接成新视频。
		cmd = [
			"ffmpeg",
			"-y",
			"-f",
			"concat",
			"-safe",
			"0",
			"-i",
			str(concat_list_path),
			"-c",
			"copy",
            "-avoid_negative_ts",
            "make_zero", # 关键参数：防止时间戳负数导致的播放器卡顿
			str(output_path),
		]
		CmdRunner.run(cmd)

	def _build_output_path(self) -> Path:
		return self.video_path.with_name(f"{self.video_path.stem}_cut{self.video_path.suffix}")

	@staticmethod
	def _format_time(seconds: float) -> str:
		hours = int(seconds // 3600)
		minutes = int((seconds % 3600) // 60)
		whole_seconds = int(seconds % 60)
		milliseconds = round((seconds - int(seconds)) * 1000)

		if milliseconds == 1000:
			whole_seconds += 1
			milliseconds = 0
		if whole_seconds == 60:
			minutes += 1
			whole_seconds = 0
		if minutes == 60:
			hours += 1
			minutes = 0

		return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"

	@staticmethod
	def _escape_concat_path(path: Path) -> str:
		return path.resolve().as_posix().replace("'", "\\'")
