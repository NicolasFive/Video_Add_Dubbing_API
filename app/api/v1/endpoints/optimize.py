import json
import pickle

from fastapi import APIRouter, HTTPException, Form

from app.models.domain import SelfCheckItem
from app.models.schemas import OptimizeDataResult, OptimizeUpdateResult, SelfCheckDataResult, CheckConfirmDataResult
from app.services.pipeline import build_stage_configs, build_stage_registry
from app.utils.file_manager import FileManager

router = APIRouter()


def _load_context(task_id: str):
    task_dir = FileManager.get_task_dir(task_id)
    context_file = task_dir / "context.pkl"
    if not context_file.exists():
        raise HTTPException(
            status_code=404, detail="context.pkl not found for this task"
        )

    try:
        with open(context_file, "rb") as f:
            return pickle.load(f), context_file
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"failed to load context.pkl: {exc}"
        ) from exc


def _resolve_stage(stage: str):
    stage_configs = build_stage_configs()
    stage_key = None
    stage_input = stage.strip().lower()
    for cfg in stage_configs:
        if stage_input == cfg.key.lower():
            stage_key = cfg.key
            break

    if not stage_key:
        raise HTTPException(status_code=400, detail=f"unknown stage: {stage}")

    stage_registry = build_stage_registry()
    stage_impl = stage_registry.get(stage_key)
    if not stage_impl:
        raise HTTPException(
            status_code=400, detail=f"stage implementation not found: {stage}"
        )
    return stage_key, stage_impl


@router.get("/{task_id}", response_model=OptimizeDataResult)
async def get_current_config(task_id: str, stage: str):
    ctx, _ = _load_context(task_id)
    stage_key, stage_impl = _resolve_stage(stage)

    if not hasattr(stage_impl, "get_data"):
        raise HTTPException(
            status_code=400, detail=f"stage does not support get_data: {stage_key}"
        )

    try:
        raw_data = stage_impl.get_data(ctx)
        if isinstance(raw_data, (dict, list)):
            data = json.dumps(raw_data, ensure_ascii=False, indent=2)
        else:
            data = str(raw_data)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"failed to read stage data: {exc}"
        ) from exc

    return OptimizeDataResult(task_id=task_id, stage=stage_key, data=data)


@router.post("/{task_id}", response_model=OptimizeUpdateResult)
async def update_current_config(
    task_id: str,
    stage: str = Form(...),
    data: str = Form(...),
):
    ctx, context_file = _load_context(task_id)
    stage_key, stage_impl = _resolve_stage(stage)

    if not hasattr(stage_impl, "set_data"):
        raise HTTPException(
            status_code=400, detail=f"stage does not support set_data: {stage_key}"
        )

    try:
        parsed_data = json.loads(data)
    except json.JSONDecodeError as exc:
        parsed_data = data  # 如果不是 JSON 格式，则直接使用原始字符串
    try:
        stage_impl.set_data(ctx, parsed_data)
        stage_impl.save_log(ctx)
        with open(context_file, "wb") as f:
            pickle.dump(ctx, f)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"failed to update stage data: {exc}"
        ) from exc

    return OptimizeUpdateResult(
        task_id=task_id,
        stage=stage_key,
        message="stage data updated",
    )

@router.get("/self_check/{task_id}", response_model=SelfCheckDataResult)
async def self_check(task_id: str, stage: str):
    ctx, _ = _load_context(task_id)
    stage_key, stage_impl = _resolve_stage(stage)

    if not hasattr(stage_impl, "self_check"):
        raise HTTPException(
            status_code=400, detail=f"stage does not support self_check: {stage_key}"
        )

    try:
        data = stage_impl.self_check(ctx)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"failed to read stage data: {exc}"
        ) from exc

    return SelfCheckDataResult(task_id=task_id, stage=stage_key, data=data)



@router.post("/check_confirm/{task_id}", response_model=CheckConfirmDataResult)
async def check_confirm(
    task_id: str,
    stage: str = Form(...),
    data: str = Form(...),
):
    ctx, context_file = _load_context(task_id)
    stage_key, stage_impl = _resolve_stage(stage)

    if not hasattr(stage_impl, "check_confirm"):
        raise HTTPException(
            status_code=400, detail=f"stage does not support check_confirm: {stage_key}"
        )

    try:
        parsed_data = json.loads(data)
        parsed_data = [SelfCheckItem(**item) for item in parsed_data]
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail=f"invalid JSON format for check_confirm data: {exc}"
        )
    try:
        stage_impl.check_confirm(ctx, parsed_data)
        stage_impl.save_log(ctx)
        with open(context_file, "wb") as f:
            pickle.dump(ctx, f)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"failed to update stage data: {exc}"
        ) from exc

    return OptimizeUpdateResult(
        task_id=task_id,
        stage=stage_key,
        message="stage data updated",
    )