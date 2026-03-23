from pathlib import Path
from app.utils.cmd_runner import CmdRunner
from app.core.config import settings

class DemucsService:
    def separate(self, audio_path: str, output_dir: str) -> tuple[str, str]:
        """
        执行 Demucs 分离人声和伴奏
        返回: (人声路径, 伴奏路径)
        """
        # 构造 demucs 命令
        # demucs -n htdemucs --two-stems=vocals --out {output_dir} {audio_path}
        cmd = [
            "demucs",
            "-n", settings.DEMUCS_MODEL,
            "--two-stems=vocals",
            "--out", output_dir,
            audio_path
        ]
        
        CmdRunner.run(cmd)
        
        # 假设 demucs 输出结构是 output_dir/{model_name}/{filename}/vocals.wav
        # 需要根据实际 demucs 版本调整路径查找逻辑
        base_name = Path(audio_path).stem
        vocals_path = Path(output_dir) / settings.DEMUCS_MODEL / base_name / "vocals.wav"
        instrumental_path = Path(output_dir) / settings.DEMUCS_MODEL / base_name / "no_vocals.wav"
        
        if not vocals_path.exists():
            raise FileNotFoundError("Demucs failed to generate vocals track")
            
        return str(vocals_path), str(instrumental_path)