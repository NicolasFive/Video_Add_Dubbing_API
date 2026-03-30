from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
import json

from app.models.domain import ProcessingContext, SelfCheckItem
from pathlib import Path


class BasePipelineStage(ABC):
    """Pipeline stage interface: every stage communicates through ProcessingContext."""

    @abstractmethod
    def run(self, ctx: ProcessingContext) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def restore(self, ctx: ProcessingContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def logfile_name(self) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def save_log(self, ctx: ProcessingContext) -> None:
        raise NotImplementedError
    
    @abstractmethod
    def read_log(self, ctx: ProcessingContext) -> str:
        raise NotImplementedError
    
    @abstractmethod
    def get_data(self, ctx: ProcessingContext) -> list[dict]| dict| str:
        raise NotImplementedError

    @abstractmethod
    def set_data(self, ctx: ProcessingContext, data: list[dict] | dict | str) -> None:
        raise NotImplementedError

    @abstractmethod
    def self_check(self, ctx: ProcessingContext) -> list[SelfCheckItem]:
        raise NotImplementedError

    @abstractmethod
    def check_confirm(self, ctx: ProcessingContext, data: list[SelfCheckItem]) -> None:
        raise NotImplementedError
    
    @staticmethod
    def _save_log(ctx: ProcessingContext, log_name: str = "", log_data=None) -> None:
        if log_data is None:
            log_data = {}

        log_path = Path(ctx.work_dir) / f"{log_name}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _read_log(ctx: ProcessingContext, log_name: str = "") -> str:
        with open(f"{ctx.work_dir}/{log_name}.json", "r", encoding="utf-8") as f:
            log_data = f.read()
            return log_data


@dataclass(frozen=True)
class PipelineStageConfig:
    """Declarative stage configuration used by pipeline scheduler."""

    key: str
    name: str
    progress: int
    enabled: bool = True
