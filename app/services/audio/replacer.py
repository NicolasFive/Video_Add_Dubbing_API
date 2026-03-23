from pathlib import Path
from app.utils.cmd_runner import CmdRunner


class FFmpegAudioReplacer:
    def replace(self, video_path: str, audio_path: str, output_path: str):
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            output_path,
        ]
        CmdRunner.run(cmd)

        if not Path(output_path).exists():
            raise FileNotFoundError("Failed to generate output video with replaced audio")