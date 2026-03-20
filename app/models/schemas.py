from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# --- 请求模型 ---
# 由于入参可能包含文件上传和普通字段，建议在 endpoint 中直接使用 FastAPI 的参数类型（UploadFile, Form 等），而不是在 Pydantic 模型中定义。


# --- 响应模型 ---
class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    UNKNOWN = "unknown"

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatusEnum
    message: Optional[str] = None
    created_at: datetime

class TaskResult(BaseModel):
    task_id: str
    status: TaskStatusEnum
    video_url: Optional[str] = None
    subtitle_url: Optional[str] = None
    error_detail: Optional[str] = None
    progress: int = Field(0, ge=0, le=100) # 进度百分比
    current_step: Optional[str] = None


class TaskFileItem(BaseModel):
    file_name: str
    relative_path: str
    size_bytes: int
    updated_at: datetime
    download_url: str


class TaskFilesResult(BaseModel):
    task_id: str
    status: TaskStatusEnum
    files: List[TaskFileItem] = Field(default_factory=list)
    progress: int = Field(0, ge=0, le=100)
    current_step: Optional[str] = None
    error_detail: Optional[str] = None


class OptimizeDataResult(BaseModel):
    task_id: str
    stage: str
    data: str


class OptimizeUpdateResult(BaseModel):
    task_id: str
    stage: str
    message: str


class PipelineConfigItem(BaseModel):
    key: str
    name: str


class PipelineConfigResult(BaseModel):
    stages: List[PipelineConfigItem] = Field(default_factory=list)

