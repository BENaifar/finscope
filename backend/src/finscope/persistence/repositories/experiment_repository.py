from sqlalchemy.orm import Session

from finscope.domain.experiment_config import ExperimentConfig
from finscope.persistence.mappings.experiment_mapper import to_domain, to_record
from finscope.persistence.models.experiment import ExperimentRecord


class ExperimentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, config: ExperimentConfig) -> None:
        self._session.add(to_record(config))
        self._session.flush()

    def get_by_id(self, experiment_id: str) -> ExperimentConfig | None:
        record = self._session.get(ExperimentRecord, experiment_id)
        return to_domain(record) if record is not None else None