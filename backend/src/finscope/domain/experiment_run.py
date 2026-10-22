
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.finscope.analytics.models.performance_result import PerformanceResult
from src.finscope.domain.experiment_config import ExperimentConfig


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ExperimentRun:
    id: str
    config: ExperimentConfig
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    status: ExperimentStatus = ExperimentStatus.PENDING
    result: PerformanceResult | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id must be a non-empty string")

        if not isinstance(self.config, ExperimentConfig):
            raise TypeError("config must be an ExperimentConfig")

        if not isinstance(self.created_at, datetime):
            raise TypeError("created_at must be a datetime")

        if self.started_at is not None and not isinstance(self.started_at, datetime):
            raise TypeError("started_at must be a datetime or None")

        if self.finished_at is not None and not isinstance(self.finished_at, datetime):
            raise TypeError("finished_at must be a datetime or None")

        if self.started_at is not None and self.created_at >= self.started_at:
            raise ValueError("created_at must be before started_at")

        if (
            self.started_at is not None
            and self.finished_at is not None
            and self.started_at >= self.finished_at
        ):
            raise ValueError("started_at must be before finished_at")

        if not isinstance(self.status, ExperimentStatus):
            raise TypeError("status must be an ExperimentStatus")

        if self.status == ExperimentStatus.PENDING:
            if self.started_at is not None or self.finished_at is not None:
                raise ValueError("a pending run cannot have start or finish times")
        elif self.status == ExperimentStatus.RUNNING:
            if self.started_at is None:
                raise ValueError("a running run must have a start time")
            if self.finished_at is not None:
                raise ValueError("a running run cannot have a finish time")
        elif self.started_at is None or self.finished_at is None:
            raise ValueError("a completed or failed run must have start and finish times")

        if self.result is not None and not isinstance(
            self.result, PerformanceResult
        ):
            raise TypeError("result must be a PerformanceResult or None")

        if self.error_message is not None and not self.error_message.strip():
            raise ValueError("error_message must be non-empty when provided")

        if self.status == ExperimentStatus.COMPLETED and self.result is None:
            raise ValueError("a completed run must have a result")

        if self.status == ExperimentStatus.FAILED and self.error_message is None:
            raise ValueError("a failed run must have an error message")

        if self.status != ExperimentStatus.COMPLETED and self.result is not None:
            raise ValueError("only a completed run can have a result")

        if self.status != ExperimentStatus.FAILED and self.error_message is not None:
            raise ValueError("only a failed run can have an error message")
