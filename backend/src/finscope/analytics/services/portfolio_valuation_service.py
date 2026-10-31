from decimal import Decimal

from finscope.analytics.models.portfolio_value_point import PortfolioValuePoint
from finscope.domain.experiment_config import ExperimentConfig
from finscope.domain.portfolio import Portfolio
from finscope.market_data.models.price_series import PriceSeries


class PortfolioValuationService:
    def calculate(
        self,
        portfolio: Portfolio,
        config: ExperimentConfig,
        price_series: tuple[PriceSeries, ...],
    ) -> tuple[PortfolioValuePoint, ...]:
        instrument_ids = {
            instrument.id
            for instrument in portfolio.instruments
        }
        price_series_by_instrument_id: dict[str, PriceSeries] = {}
        for series in price_series:
            instrument_id = series.instrument.id
            if instrument_id not in instrument_ids:
                continue
            if instrument_id in price_series_by_instrument_id:
                raise ValueError(
                    f"Multiple price series found for instrument {instrument_id}"
                )
            price_series_by_instrument_id[instrument_id] = series

        missing_series = instrument_ids - price_series_by_instrument_id.keys()
        if missing_series:
            missing_instruments = ", ".join(sorted(missing_series))
            raise ValueError(
                f"Missing price series for portfolio instruments: {missing_instruments}"
            )

        prices_by_instrument_id = {
            instrument_id: {
                point.date: point.adjusted_close
                for point in series.points
                if config.start_date <= point.date <= config.end_date
            }
            for instrument_id, series in price_series_by_instrument_id.items()
        }
        valuation_dates = sorted(
            {
                valuation_date
                for prices in prices_by_instrument_id.values()
                for valuation_date in prices
            }
        )
        if not valuation_dates:
            raise ValueError(
                "No price data found within the configured valuation period"
            )

        for valuation_date in valuation_dates:
            for instrument_id, prices in prices_by_instrument_id.items():
                if valuation_date not in prices:
                    raise ValueError(
                        f"Missing price for instrument {instrument_id} "
                        f"on {valuation_date}"
                    )

        initial_date = valuation_dates[0]
        initial_quantities = {
            instrument_id: (
                portfolio.initial_capital
                * portfolio.get_weight(instrument_id)
                / prices_by_instrument_id[instrument_id][initial_date]
            )
            for instrument_id in sorted(instrument_ids)
        }

        portfolio_valuations: list[PortfolioValuePoint] = []
        for valuation_date in valuation_dates:
            value = sum(
                (
                    prices_by_instrument_id[instrument_id][valuation_date]
                    * quantity
                    for instrument_id, quantity in initial_quantities.items()
                ),
                start=Decimal(0),
            )

            portfolio_valuations.append(
                PortfolioValuePoint(
                    valuation_date=valuation_date,
                    total_value=value,
                )
            )

        return tuple(portfolio_valuations)