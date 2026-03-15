from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.domain import ProcessingContext


class BasePipelineStage(ABC):
    """Pipeline stage interface: every stage communicates through ProcessingContext."""

    @abstractmethod
    def run(self, ctx: ProcessingContext) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class PipelineStageConfig:
    """Declarative stage configuration used by pipeline scheduler."""

    key: str
    name: str
    progress: int
    enabled: bool = True
