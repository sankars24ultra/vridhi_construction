"""Company-wide cash transactions and manually confirmed project results."""
from alembic import op
import sqlalchemy as sa

revision = "0019_company_cashbook"
down_revision = "0018_project_audit"
branch_labels = None
depends_on = None


def common_columns():
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("request_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("recorded_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("void_reason", sa.String(500), nullable=True),
    ]


def upgrade() -> None:
    op.add_column("users", sa.Column("cashbook_permissions", sa.JSON(), nullable=True))
    op.create_table(
        "company_cash_entries", *common_columns(),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("party", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("account", sa.String(100), nullable=False),
        sa.Column("payment_mode", sa.String(24), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=True),
        sa.CheckConstraint("amount > 0", name="ck_company_cash_positive"),
    )
    op.create_index("ix_company_cash_entries_transaction_date", "company_cash_entries", ["transaction_date"])
    op.create_table(
        "company_project_results", *common_columns(),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("basis", sa.String(500), nullable=False),
    )
    op.create_index("ix_company_project_results_project_id", "company_project_results", ["project_id"])
    op.create_index("uq_company_project_result_active_date", "company_project_results", ["project_id", "as_of"], unique=True, postgresql_where=sa.text("voided_at IS NULL"))


def downgrade() -> None:
    op.drop_table("company_project_results")
    op.drop_table("company_cash_entries")
    op.drop_column("users", "cashbook_permissions")
