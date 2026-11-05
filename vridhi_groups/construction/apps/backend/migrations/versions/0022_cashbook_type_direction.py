"""Snapshot cash direction per entry and configure it per transaction type."""
from alembic import op
import sqlalchemy as sa

revision = "0022_cashbook_type_direction"
down_revision = "0021_cashbook_options"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("company_cash_options", sa.Column("direction", sa.String(3), nullable=True))
    op.add_column("company_cash_entries", sa.Column("direction", sa.String(3), nullable=True))
    direction = "CASE WHEN kind IN ('owner_capital', 'project_received', 'other_receipt', 'opening_in') THEN 'in' ELSE 'out' END"
    op.execute(sa.text(f"UPDATE company_cash_entries SET direction = {direction}"))
    op.execute(sa.text(f"UPDATE company_cash_options SET direction = {direction} WHERE option_type = 'type'"))
    op.alter_column("company_cash_entries", "direction", nullable=False)
    op.create_check_constraint("ck_cash_entry_direction", "company_cash_entries", "direction IN ('in', 'out')")
    op.create_check_constraint("ck_cash_option_direction", "company_cash_options", "(option_type = 'category' AND direction IS NULL) OR (option_type = 'type' AND direction IS NOT NULL AND direction IN ('in', 'out'))")


def downgrade():
    op.drop_constraint("ck_cash_option_direction", "company_cash_options")
    op.drop_constraint("ck_cash_entry_direction", "company_cash_entries")
    op.drop_column("company_cash_entries", "direction")
    op.drop_column("company_cash_options", "direction")
