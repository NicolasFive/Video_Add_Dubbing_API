from fastapi import APIRouter
from app.models.schemas import PipelineConfigItem, PipelineConfigResult
from app.services.pipeline.registry import build_stage_configs, get_available_line_types
from typing import Optional

router = APIRouter()

@router.get("/config", response_model=PipelineConfigResult)
async def get_config(line_type: Optional[str] = None):
    """获取指定 line_type 的 Pipeline 配置
    
    Args:
        line_type: 配置类型，如果为空则使用默认值 'default'
        
    Returns:
        PipelineConfigResult: 包含该 line_type 的所有 stages 配置
    """
    if not line_type:
        line_type = "default"
    stages = build_stage_configs(line_type)
    return PipelineConfigResult(
        stages=[PipelineConfigItem(key=stage.key, name=stage.name) for stage in stages]
    )


@router.get("/line-types", response_model=dict)
async def get_all_line_types():
    """获取所有可用的 line_type
    
    Returns:
        dict: 包含 line_types 列表
    """
    line_types = get_available_line_types()
    return {"line_types": line_types}