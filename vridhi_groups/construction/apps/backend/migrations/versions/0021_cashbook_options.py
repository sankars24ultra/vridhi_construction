"""Custom company cashbook categories (top level) and transaction types (second level)."""
from alembic import op
import sqlalchemy as sa

revision = "0021_cashbook_options"
down_revision = "0020_project_result_approval"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "company_cash_options",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("option_type", sa.String(16), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("parent", sa.String(80), nullable=False, server_default=""),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("normalized_name", sa.String(240), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("option_type", "kind", "parent", "normalized_name"),
    )
    op.add_column("company_cash_entries", sa.Column("custom_category", sa.String(80), nullable=True))


def downgrade():
    op.drop_column("company_cash_entries", "custom_category")
    op.drop_table("company_cash_options")
