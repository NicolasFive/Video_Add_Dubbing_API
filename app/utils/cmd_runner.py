import subprocess
import logging
from app.core.exceptions import FileProcessingError

logger = logging.getLogger(__name__)

class CmdRunner:
    @staticmethod
    def run(command: list[str], cwd: str = None) -> str:
        try:
            logger.info(f"Running command: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True, # 抛出异常如果返回码非 0
                timeout=3600 # 防止死锁
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            raise FileProcessingError(f"Command failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise FileProcessingError("Command timed out")