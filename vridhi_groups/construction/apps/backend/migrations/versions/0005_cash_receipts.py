from alembic import op
import sqlalchemy as sa


revision = "0005_cash_receipts"
down_revision = "0004_purchase_order_image"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cash_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("billing_entry_id", sa.Uuid(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_method", sa.String(24), server_default="Other", nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("recorded_by_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["billing_entry_id"], ["billing_entries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cash_receipts_project_id", "cash_receipts", ["project_id"])
    op.create_index("ix_cash_receipts_billing_entry_id", "cash_receipts", ["billing_entry_id"])
    op.create_index("ix_cash_receipts_received_date", "cash_receipts", ["received_date"])


def downgrade() -> None:
    op.drop_index("ix_cash_receipts_received_date", table_name="cash_receipts")
    op.drop_index("ix_cash_receipts_billing_entry_id", table_name="cash_receipts")
    op.drop_index("ix_cash_receipts_project_id", table_name="cash_receipts")
    op.drop_table("cash_receipts")
