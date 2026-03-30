from __future__ import annotations

import logging
import pickle
from typing import Callable

from app.core.exceptions import AppException
from app.models.domain import ProcessingContext
from app.services.pipeline import (
    BasePipelineStage,
    PipelineStageConfig,
    build_stage_configs,
    build_stage_registry,
)
from pathlib import Path

logger = logging.getLogger(__name__)


class DubbingPipeline:
    # 初始化 Pipeline：装载上下文、流程配置与环节注册表
    def __init__(
        self,
        context: ProcessingContext,
        stage_configs: list[PipelineStageConfig] | None = None,
        stage_registry: dict[str, BasePipelineStage] | None = None,
    ):
        # 保存上下文，作为各环节之间的数据桥梁
        self.ctx = context
        # 使用外部传入配置，未传入时使用默认流程配置
        self.stage_configs = stage_configs or build_stage_configs()
        # 构建默认环节实现注册表
        self.stage_registry = build_stage_registry()
        # 允许外部覆盖或扩展环节实现
        if stage_registry:
            self.stage_registry.update(stage_registry)
        # 判断 stage 的有效性
        self._validate_stage_configs()

    # 整体替换流程配置
    def set_stage_configs(self, stage_configs: list[PipelineStageConfig]) -> None:
        # 更新流程配置并立即校验
        self.stage_configs = stage_configs
        self._validate_stage_configs()

    # 新增一个流程环节，支持指定插入位置
    def add_stage(
        self,
        stage_config: PipelineStageConfig,
        stage_impl: BasePipelineStage,
        index: int | None = None,
    ) -> None:
        # 先注册实现，再把配置加入执行链
        self.stage_registry[stage_config.key] = stage_impl
        if index is None:
            self.stage_configs.append(stage_config)
        else:
            self.stage_configs.insert(index, stage_config)
        # 判断 stage 的有效性
        self._validate_stage_configs()

    # 按 key 删除流程环节
    def remove_stage(self, stage_key: str) -> None:
        # 仅删除配置，不移除注册表中的实现，便于后续复用
        self.stage_configs = [cfg for cfg in self.stage_configs if cfg.key != stage_key]

    # 替换已有环节实现，并可选替换环节配置
    def replace_stage(
        self,
        stage_key: str,
        stage_impl: BasePipelineStage,
        stage_config: PipelineStageConfig | None = None,
    ) -> None:
        # 替换注册表中的实现
        self.stage_registry[stage_key] = stage_impl
        if stage_config:
            # 用新配置替换同 key 的已有配置
            updated = []
            for cfg in self.stage_configs:
                updated.append(stage_config if cfg.key == stage_key else cfg)
            self.stage_configs = updated
            # 判断 stage 的有效性
            self._validate_stage_configs()

    # 执行流程调度主入口
    def run(
        self,
        update_progress_callback: Callable[[str, int], None] | None = None,
        start_step: str = None,
        end_step: str = None,
    ) -> ProcessingContext:
        # 执行完整流程
        # update_progress_callback: func(step_name, progress_percent)
        # start_step: 从哪个步骤开始执行，用于断点续传
        try:
            # 根据 start_step 解析本次需要执行的环节列表
            execution_stages = self._resolve_execution_stages(start_step)
            for stage_cfg in execution_stages:
                key = stage_cfg.key
                progress = stage_cfg.progress
                # 回调上报当前环节进度
                if update_progress_callback:
                    update_progress_callback(key, progress)
                logger.info(f"Task {self.ctx.task_id}: {key}...")
                # 记录当前环节，便于失败后断点续传
                self.ctx.current_step = key
                # 调用具体环节实现
                self._run_stage(stage_cfg)
                # 保存上下文以支持断点续传
                context_temp_file = Path(self.ctx.work_dir) / "context_temp.pkl"
                with open(context_temp_file, "wb") as f:
                    pickle.dump(self.ctx, f)
                context_file = Path(self.ctx.work_dir) / "context.pkl"
                if context_file.exists():
                    context_file.unlink()
                context_temp_file.rename(Path(self.ctx.work_dir) / "context.pkl")
                # 判断是否设置结束步骤，是则判断当前是否需要结束
                if end_step and stage_cfg.key == end_step:
                    break

            # 全部执行完成后统一上报Completed，但是进度仍然保持最后一个环节的值
            if update_progress_callback:
                update_progress_callback("Completed", progress)
            logger.info(f"Task {self.ctx.task_id} Success!")

            return self.ctx

        except Exception as e:
            # 统一日志与异常封装
            logger.exception(f"Task {self.ctx.task_id} Failed: {str(e)}")
            raise AppException(str(e))

    # 解析执行链：过滤未启用环节，并处理起始环节定位
    def _resolve_execution_stages(self, start_step: str | None) -> list[PipelineStageConfig]:
        # 只保留启用状态的环节
        enabled_stages = [cfg for cfg in self.stage_configs if cfg.enabled]
        start_index = 0
        if start_step:
            # 支持通过 key 匹配起始环节
            for i, cfg in enumerate(enabled_stages):
                if cfg.key == start_step:
                    start_index = i
                    break
        # 返回从起始环节到末尾的执行列表
        return enabled_stages[start_index:]


    # 执行单个环节
    def _run_stage(self, stage_cfg: PipelineStageConfig) -> None:
        # 读取环节实现
        stage = self.stage_registry.get(stage_cfg.key)
        # 判断 stage 的有效性
        if not stage:
            raise ValueError(f"No stage implementation registered for key: {stage_cfg.key}")
        # 通过 ctx 与其他环节协作
        try:
            if not self.ctx.no_cache:
                success = stage.restore(self.ctx)
            else:
                success = False
                
            if not success:
                stage.run(self.ctx)
                stage.save_log(self.ctx)
            else:
                logger.info(f"Task {self.ctx.task_id}: {stage_cfg.key} restored from log, skipped execution.")
        except Exception as e:
            stage.run(self.ctx)
            stage.save_log(self.ctx)

    # 校验流程配置与注册表的一致性
    def _validate_stage_configs(self) -> None:
        # 判断配置列表是否为空
        if not self.stage_configs:
            raise ValueError("stage_configs cannot be empty")

        # 判断是否存在重复 key，并验证每个 key 都有实现
        seen = set()
        for cfg in self.stage_configs:
            if cfg.key in seen:
                raise ValueError(f"duplicated stage key in stage_configs: {cfg.key}")
            seen.add(cfg.key)
            if cfg.key not in self.stage_registry:
                raise ValueError(f"stage key has no implementation: {cfg.key}")

        # 检查进度值顺序，仅做提醒，不影响执行顺序
        sorted_by_progress = sorted(self.stage_configs, key=lambda item: item.progress)
        if sorted_by_progress != self.stage_configs:
            logger.warning(
                "stage_configs progress is not in ascending order; execution still follows stage_configs order"
            )
