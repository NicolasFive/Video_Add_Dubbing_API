from fastapi import APIRouter
from app.models.schemas import PipelineConfigItem, PipelineConfigResult
from app.services.pipeline.registry import build_stage_configs

router = APIRouter()

@router.get("/config", response_model=PipelineConfigResult)
async def get_config():
    stages = build_stage_configs()
    return PipelineConfigResult(
        stages=[PipelineConfigItem(key=stage.key, name=stage.name) for stage in stages]
    )