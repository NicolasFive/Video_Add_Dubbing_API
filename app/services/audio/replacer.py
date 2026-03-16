from pathlib import Path
from app.utils.cmd_runner import CmdRunner


class FFmpegAudioReplacer:
    def replace(self, video_path: Path, audio_path: Path, output_path: Path):
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "copy",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            str(output_path),
        ]
        CmdRunner.run(cmd)

        if not output_path.exists():
            raise FileNotFoundError("Failed to generate output video with replaced audio")