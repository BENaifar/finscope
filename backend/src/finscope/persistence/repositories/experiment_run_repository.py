from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from finscope.domain.experiment_run import ExperimentRun
from finscope.persistence.mappings.experiment_run_mapper import (
    apply_state,
    to_domain,
    to_record,
)
from finscope.persistence.models.experiment_run import ExperimentRunRecord


class ExperimentRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: ExperimentRun) -> None:
        self._session.add(to_record(run))
        self._session.flush()

    def get_by_id(self, run_id: str) -> ExperimentRun | None:
        record = self._load(run_id)
        return to_domain(record) if record is not None else None

    def update(self, run: ExperimentRun) -> None:
        record = self._load(run.id)
        if record is None:
            raise LookupError(f"experiment run {run.id} does not exist")
        if record.experiment_id != run.config.id:
            raise ValueError("a run cannot move to a different experiment")
        apply_state(record, run)
        self._session.flush()

    def _load(self, run_id: str) -> ExperimentRunRecord | None:
        # populate_existing refreshes an instance already in the session, so a
        # get right after add/update never returns stale relationship state.
        return self._session.scalar(
            select(ExperimentRunRecord)
            .where(ExperimentRunRecord.id == run_id)
            .options(
                joinedload(ExperimentRunRecord.experiment),
                joinedload(ExperimentRunRecord.metrics),
                selectinload(ExperimentRunRecord.value_points),
            )
            .execution_options(populate_existing=True)
        )