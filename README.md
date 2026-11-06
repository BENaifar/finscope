# FinScope

FinScope is a backend for portfolio backtesting and analysis. You define a portfolio of US-listed stocks and ETFs, pick a start date, an end date and an amount of capital, and FinScope simulates a buy-and-hold investment over that period. It then computes the portfolio's value over time and its performance metrics, and saves every execution attempt with its result or its failure reason.

The project is built as an engineering exercise in correctness and clear boundaries. Feature count is a lower priority. Money is handled with `Decimal` throughout. Missing market data is reported and never forward-filled. Domain logic has no dependency on the database or the data provider.

> **Status:** backend in active development. The domain, analytics, market data, persistence and application layers are implemented and tested. An HTTP API is in progress and not yet committed. There is no frontend.

---

## Contents

- [What it does](#what-it-does)
- [Architecture](#architecture)
- [Calculation semantics](#calculation-semantics)
- [Market data](#market-data)
- [Persistence](#persistence)
- [Getting started](#getting-started)
- [Testing](#testing)
- [Project layout](#project-layout)
- [Scope and limitations](#scope-and-limitations)
- [Roadmap](#roadmap)

---

## What it does

1. **Load a saved experiment.** An experiment is a portfolio plus a start date, end date and initial capital.
2. **Create a run.** Each execution attempt is its own `ExperimentRun` record with a status and timestamps. One experiment can have many runs.
3. **Fetch prices.** Stored prices are used where they exist. Only trading days that are actually missing are fetched from a provider, and the new prices are cached.
4. **Analyse.** Buy fixed quantities on the first trading day, value the portfolio every day, and compute the metrics.
5. **Save the outcome.** The run ends as `COMPLETED` with its value series and metrics, or as `FAILED` with an error message.

## Architecture

FinScope is a modular monolith with strict layer boundaries:

```text
application   ExperimentWorkflowService (use case, owns the commit points)
    │
    ├── market_data   MarketDataService: store first, then providers, then a gap check
    ├── persistence   SQLAlchemy ORM models, mappers, repositories
    └── analytics     valuation, performance metrics, orchestration
            │
          domain      frozen dataclasses with validated invariants
```

**Design principles**

- **Domain stays independent of infrastructure.** `Instrument`, `Portfolio`, `ExperimentConfig` and `ExperimentRun` are frozen dataclasses. They are never ORM models, API schemas or provider-specific structures.
- **Four model families, kept separate.** These are domain inputs (`Portfolio`, `PriceSeries`), analytics results (`PortfolioValuePoint`, `PerformanceMetrics`, `PerformanceResult`), ORM models, and (in future) API DTOs. Explicit mappers in `persistence/mappings` translate between domain and ORM.
- **Dependencies are injected as ports.** Services depend on `Protocol`s such as `PriceHistoryProvider`, `PriceStore`, `TradingCalendar`, `RunStore` and `RunOrchestrator`, not on concrete classes. Tests replace them with fakes, so unit tests never touch the network or the database.
- **The caller owns the transaction.** Repositories and `MarketDataService` never commit. `ExperimentWorkflowService` commits exactly twice: once after saving the `PENDING` run, so the attempt is recorded even if execution crashes, and once after saving the final state.
- **An experiment is not a run.** Runs follow an enforced lifecycle: `PENDING → RUNNING → COMPLETED | FAILED`. `ExperimentRun` rejects invalid combinations, such as a completed run with no result, a failed run with no error message, or timestamps that are naive or out of order.

## Calculation semantics

| Concept | Definition |
|---|---|
| Quantity bought | `q_i = C · w_i / P_i,0`, where `P_i,0` is the first eligible price on or after the start date |
| Portfolio value | `V_t = Σ q_i · P_i,t` |
| Total return | `(V_final − V_initial) / V_initial` |
| Max drawdown | Largest decline from a peak to a later trough, relative to that peak. This is not the worst single-day return. |
| Other metrics | Profit/loss, best daily return and its date, highest and lowest portfolio values and their dates, drawdown peak and trough dates |

The strategy is **buy-and-hold**. Quantities are fixed at the start and weights drift with prices. Fractional shares are allowed. All prices and values are `Decimal`.

**Reference case:** $10,000 split 60% A (100 → 110 → 90) and 40% B (50 → 55 → 60) buys 60 units of A and 80 units of B. The portfolio is worth 10,000, then 11,000, then 10,200, a total return of 2%.

## Market data

- **Provider abstraction.** `PriceHistoryProvider` is a Protocol with three implementations: Yahoo Finance (via `yfinance`, with an injected loader and failures wrapped in `MarketDataError`), CSV, and in-memory.
- **Calendar-aware gap detection.** Expected dates come from a trading calendar (NYSE via `exchange_calendars`), so weekends and exchange holidays are never treated as missing data.
- **Read-through cache.** `MarketDataService` is itself a `PriceHistoryProvider`. It reads the store first and asks providers only for the range between the first and last missing date. It writes back only the dates that were missing and never overwrites stored prices or their provenance.
- **No silent assumptions.**
  - Gaps that remain unresolved raise `IncompleteMarketDataError`.
  - Dates before an instrument's first available price are treated as "not yet trading", for example before a listing.
  - A provider error other than "no data" is raised immediately, not hidden by falling back to another provider.
- **Provenance.** Each stored price records which provider supplied it and when.

## Persistence

PostgreSQL 17 (Docker Compose), SQLAlchemy 2.0, psycopg 3 and Alembic.

| Table | Purpose |
|---|---|
| `instruments` | Tradable symbols, with check constraints |
| `price_points` | Daily adjusted closes. Unique per instrument and date, written with idempotent upserts, with provider provenance |
| `portfolios`, `portfolio_allocations` | Saved portfolios. Deleting a portfolio cascades to its allocations. Deleting an instrument still used by a portfolio is restricted |
| `experiments` | Saved experiment configurations |
| `experiment_runs` | Execution attempts with status, timestamps and error message |
| `portfolio_value_points`, `performance_metrics` | Results of a completed run |

`PriceSeries` is rebuilt from `price_points` rows and has no table of its own. `PerformanceResult` is a grouping of outputs and has no table of its own either. The schema is managed entirely by Alembic migrations in `backend/migrations/versions`.

## Getting started

**Requirements:** Python 3.11+, Docker. Commands below are for PowerShell and are run from `backend/`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

**Configure the environment.** Copy the template and replace the placeholder password:

```powershell
Copy-Item .env.example .env
```

| Variable | Used by |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Docker Compose |
| `DATABASE_URL` | The application (`postgresql+psycopg://...`) |
| `TEST_DATABASE_URL` | Integration tests. The database name must end in `_test` |

`.env` is git-ignored. Credentials are never hardcoded.

**Start PostgreSQL and apply migrations:**

```powershell
docker compose up -d
alembic upgrade head
```

The database binds to `127.0.0.1:5432` only.

## Testing

```powershell
pytest                     # full suite
pytest tests/unit -v       # unit tests only (no database needed)
pytest tests/integration   # requires PostgreSQL and TEST_DATABASE_URL
ruff check .               # lint: E, F, I, UP; line length 88
```

- **Unit tests** mirror the source tree and use fakes from `tests/fixtures`.
- **Integration tests** run against a real PostgreSQL database.
  - They are skipped when `TEST_DATABASE_URL` is unset.
  - They refuse to run unless the database name ends in `_test`.
  - Migrations are applied before the tests start.
  - Each test runs inside a transaction that is rolled back afterwards, so tests stay isolated.
  - Coverage includes repository constraints, upsert idempotency, `Decimal` round-trips, database-backed price caching, and a full experiment workflow end to end.

## Project layout

```text
backend/
├── compose.yaml               # PostgreSQL service
├── alembic.ini
├── migrations/versions/       # schema history
├── src/finscope/
│   ├── domain/                # Instrument, Portfolio, ExperimentConfig, ExperimentRun
│   ├── analytics/
│   │   ├── models/            # PortfolioValuePoint, PerformanceMetrics, PerformanceResult
│   │   └── services/          # valuation, performance, analysis engine, orchestration
│   ├── market_data/
│   │   ├── models/            # PricePoint, PriceSeries
│   │   ├── providers/         # Protocol + Yahoo, CSV, in-memory
│   │   ├── market_data_service.py
│   │   ├── coverage.py        # missing-date detection
│   │   └── nyse_trading_calendar.py
│   ├── persistence/
│   │   ├── database.py        # engine + session factory from DATABASE_URL
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── mappings/          # domain <-> ORM mappers
│   │   └── repositories/
│   └── application/           # ExperimentWorkflowService, ports, errors
└── tests/
    ├── fixtures/              # factories, fakes, CSV price history
    ├── unit/
    └── integration/
```

## Scope and limitations

The current MVP is intentionally narrow:

- **Strategy and assets:** buy-and-hold only, with no rebalancing. US-listed stocks and ETFs only, priced in USD.
- **Interfaces:** no HTTP API or frontend yet. Runs execute synchronously, with no background workers.
- **Run recovery:** a process crash during execution leaves a committed `PENDING` run, and nothing recovers it yet.
- **Market data licensing:** Yahoo Finance data is accessed via `yfinance`. Its terms for storing and redistributing data must be reviewed before any public deployment.

## Roadmap

- [x] Core analytics: valuation, metrics, run lifecycle, orchestration
- [x] Local database foundations: Docker Compose, Alembic, first migrations
- [x] Persistence: ORM models, mappers, repositories, integration tests
- [x] Market-data persistence: upserts, coverage checks, `PriceSeries` reconstruction
- [x] Experiment persistence and end-to-end workflow service
- [ ] FastAPI layer: DTOs, endpoints, validation
- [ ] Frontend (React + TypeScript)
- [ ] Deployment: data licensing review, secrets, backups, logging

## License

[Apache License 2.0](LICENSE)
