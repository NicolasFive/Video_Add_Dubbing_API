from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

from app.models.domain import ProcessingContext


class BasePipelineStage(ABC):
    """Pipeline stage interface: every stage communicates through ProcessingContext."""

    @abstractmethod
    def run(self, ctx: ProcessingContext) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_data(self, ctx: ProcessingContext) -> list[dict]| dict| str:
        raise NotImplementedError

    @abstractmethod
    def set_data(self, ctx: ProcessingContext, data: list[dict] | dict | str) -> None:
        raise NotImplementedError

    @staticmethod
    def _save_log(ctx: ProcessingContext, log_name: str = "", log_data=None) -> None:
        if log_data is None:
            log_data = {}
        log_path = ctx.work_dir / f"{log_name}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)


@dataclass(frozen=True)
class PipelineStageConfig:
    """Declarative stage configuration used by pipeline scheduler."""

    key: str
    name: str
    progress: int
    enabled: bool = True
