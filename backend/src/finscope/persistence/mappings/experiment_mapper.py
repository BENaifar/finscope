from finscope.domain.experiment_config import ExperimentConfig
from finscope.persistence.models.experiment import ExperimentRecord


def to_record(config: ExperimentConfig) -> ExperimentRecord:
    return ExperimentRecord(
        id=config.id,
        portfolio_id=config.portfolio_id,
        start_date=config.start_date,
        end_date=config.end_date,
        price_convention=config.price_convention,
    )


def to_domain(record: ExperimentRecord) -> ExperimentConfig:
    return ExperimentConfig(
        id=record.id,
        portfolio_id=record.portfolio_id,
        start_date=record.start_date,
        end_date=record.end_date,
        price_convention=record.price_convention,
    )