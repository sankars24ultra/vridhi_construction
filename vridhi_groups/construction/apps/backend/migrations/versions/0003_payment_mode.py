from alembic import op
from sqlalchemy import inspect, Column, String

revision = "0003_payment_mode"
down_revision = "0002_project_value_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "payment_mode" not in {column["name"] for column in inspect(op.get_bind()).get_columns("purchase_order_payments")}:
        op.add_column("purchase_order_payments", Column("payment_mode", String(24), nullable=False, server_default="Other"))


def downgrade() -> None:
    op.drop_column("purchase_order_payments", "payment_mode")