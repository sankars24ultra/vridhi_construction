from alembic import op
import sqlalchemy as sa


revision = "0006_inventory_details"
down_revision = "0005_cash_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop unique constraint on purchase_order_line_id so multiple receipts/issues can reference a line
    op.drop_constraint("inventory_transactions_purchase_order_line_id_key", "inventory_transactions", type_="unique")
    op.add_column("inventory_transactions", sa.Column("reference", sa.String(100), nullable=True))
    op.add_column("inventory_transactions", sa.Column("notes", sa.String(500), nullable=True))
    op.add_column("inventory_transactions", sa.Column("recorded_by_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_inventory_transactions_recorded_by_id",
        "inventory_transactions",
        "users",
        ["recorded_by_id"],
        ["id"],
        ondelete="SET NULL"
    )
    op.create_index("ix_inventory_transactions_occurred_at", "inventory_transactions", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_inventory_transactions_occurred_at", table_name="inventory_transactions")
    op.drop_constraint("fk_inventory_transactions_recorded_by_id", "inventory_transactions", type_="foreignkey")
    op.drop_column("inventory_transactions", "recorded_by_id")
    op.drop_column("inventory_transactions", "notes")
    op.drop_column("inventory_transactions", "reference")
    op.create_unique_constraint("inventory_transactions_purchase_order_line_id_key", "inventory_transactions", ["purchase_order_line_id"])
