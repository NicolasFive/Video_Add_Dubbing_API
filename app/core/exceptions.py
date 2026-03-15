class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class FileProcessingError(AppException):
    """文件处理失败 (Demucs/FFmpeg)"""
    pass

class ExternalAPIError(AppException):
    """第三方 API 调用失败 (AssemblyAI/Volcano)"""
    pass

class TaskNotFoundError(AppException):
    """任务未找到"""
    def __init__(self, task_id: str):
        super().__init__(f"Task {task_id} not found", status_code=404)

class TTSSpeedRatioTooHighError(AppException):
    """TTS 速率过高可能导致音质问题"""
    def __init__(self, speed_ratio: float):
        super().__init__(f"Calculated speed_ratio {speed_ratio} is too high, which may lead to poor audio quality.")