"""add instrument check constraints

Revision ID: 5e187a771ee8
Revises: 89d5b23584f2
Create Date: 2026-10-31 20:25:01.153655

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5e187a771ee8'
down_revision: str | Sequence[str] | None = '89d5b23584f2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add check constraints to instruments."""
    op.create_check_constraint(
        op.f("ck_instruments_symbol_not_blank"),
        "instruments",
        "length(trim(symbol)) > 0",
    )
    op.create_check_constraint(
        op.f("ck_instruments_name_not_blank"),
        "instruments",
        "length(trim(name)) > 0",
    )
    op.create_check_constraint(
        op.f("ck_instruments_currency_usd_only"),
        "instruments",
        "currency = 'USD'",
    )


def downgrade() -> None:
    """Remove check constraints from instruments."""
    op.drop_constraint(
        op.f("ck_instruments_currency_usd_only"), "instruments", type_="check"
    )
    op.drop_constraint(
        op.f("ck_instruments_name_not_blank"), "instruments", type_="check"
    )
    op.drop_constraint(
        op.f("ck_instruments_symbol_not_blank"), "instruments", type_="check"
    )