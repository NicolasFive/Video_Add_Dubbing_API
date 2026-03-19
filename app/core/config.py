from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # --- 应用配置 ---
    APP_NAME: str = "Video Dubbing API"
    LOG_LEVEL: str = "INFO"
    SERVER_PORT: int = 8000
    SERVER_HOST: str = "0.0.0.0"
    SSL_KEYFILE: Optional[str] = None
    SSL_CERTFILE: Optional[str] = None
    
    # --- 存储路径 ---
    STORAGE_ROOT: str = "./storage"
    TEMP_DIR: str = "temp"
    
    # --- 外部 API Keys ---
    ASSEMBLYAI_KEY: str
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: Optional[str] = "https://api.openai.com/v1"
    S3_ENDPOINT:str = "https://example-s3-endpoint.com"
    S3_ACCESS_KEY:str = "xxxxx"
    S3_SECRET_KEY:str = "xxxxx"
    S3_BUCKET:str = "bucket-name"
    VOLCANO_TTS_V1_APPID: str = "0000000"
    VOLCANO_TTS_V1_ACCESS_TOKEN: str = "xxxxxxxxxxx"
    VOLCANO_TTS_V2_APPID: str = "0000000"
    VOLCANO_TTS_V2_ACCESS_TOKEN: str = "xxxxxxxxxxx"
    
    # --- 工具配置 ---
    DEMUCS_MODEL: str = "htdemucs"  # 人声分离模型
    FFMPEG_BIN: str = "ffmpeg"      # ffmpeg 命令路径
    
    # --- 异步任务配置 ---
    REDIS_URL: Optional[str] = None
    CELERY_BROKER_URL: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

# 全局单例
settings = Settings()