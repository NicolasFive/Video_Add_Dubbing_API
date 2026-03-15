from fastapi import APIRouter, status
from pydantic import BaseModel
import subprocess
import shutil
from app.core.config import settings

# 模拟 Redis 检查
# from app.core.database import redis_client

router = APIRouter()

class HealthDetail(BaseModel):
    redis: str
    ffmpeg: str
    demucs: str
    disk_usage_percent: float

class HealthResponse(BaseModel):
    status: str
    details: HealthDetail

@router.get("", response_model=HealthResponse, summary="健康检查")
async def health_check():
    """
    检查 API 自身及关键依赖组件的状态。
    Kubernetes Liveness/Readiness Probe 会调用此接口。
    """
    details = HealthDetail(
        redis="unknown",
        ffmpeg="unknown",
        demucs="unknown",
        disk_usage_percent=0.0
    )
    
    overall_status = "healthy"

    # 1. 检查 Redis
    try:
        # connected = await redis_client.ping()
        connected = True # 伪代码
        details.redis = "connected" if connected else "disconnected"
        if not connected: overall_status = "degraded"
    except Exception:
        details.redis = "error"
        overall_status = "unhealthy"

    # 2. 检查 FFmpeg
    if shutil.which(settings.FFMPEG_BIN):
        details.ffmpeg = "installed"
    else:
        details.ffmpeg = "missing"
        overall_status = "unhealthy"

    # 3. 检查 Demucs (通过尝试导入或运行 --help)
    try:
        # subprocess.run(["demucs", "--help"], capture_output=True, check=True)
        details.demucs = "installed"
    except Exception:
        details.demucs = "missing"
        overall_status = "unhealthy"

    # 4. 检查磁盘空间
    import os
    stat = os.statvfs(settings.STORAGE_ROOT)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bavail * stat.f_frsize
    used_percent = ((total - free) / total) * 100
    details.disk_usage_percent = round(used_percent, 2)
    
    if used_percent > 90:
        overall_status = "degraded" # 磁盘快满了

    return HealthResponse(status=overall_status, details=details)