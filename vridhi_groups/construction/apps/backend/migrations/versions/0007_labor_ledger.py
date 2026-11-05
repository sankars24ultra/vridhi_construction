from alembic import op
import sqlalchemy as sa


revision = "0007_labor_ledger"
down_revision = "0006_inventory_details"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labor_workers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("trade", sa.String(100), nullable=False, server_default="General labor"),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_labor_workers_project_id", "labor_workers", ["project_id"])
    op.create_table(
        "labor_work_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.Uuid(), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(240), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(12), nullable=False, server_default="day"),
        sa.Column("rate", sa.Numeric(18, 2), nullable=False),
        sa.Column("recorded_by_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["worker_id"], ["labor_workers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_labor_work_entries_project_id", "labor_work_entries", ["project_id"])
    op.create_index("ix_labor_work_entries_worker_id", "labor_work_entries", ["worker_id"])
    op.create_index("ix_labor_work_entries_work_date", "labor_work_entries", ["work_date"])
    op.create_table(
        "labor_wage_payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("worker_id", sa.Uuid(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_mode", sa.String(24), nullable=False, server_default="Cash"),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("comment", sa.String(500), nullable=True),
        sa.Column("recorded_by_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["worker_id"], ["labor_workers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_labor_wage_payments_project_id", "labor_wage_payments", ["project_id"])
    op.create_index("ix_labor_wage_payments_worker_id", "labor_wage_payments", ["worker_id"])
    op.create_index("ix_labor_wage_payments_payment_date", "labor_wage_payments", ["payment_date"])


def downgrade() -> None:
    op.drop_index("ix_labor_wage_payments_payment_date", table_name="labor_wage_payments")
    op.drop_index("ix_labor_wage_payments_worker_id", table_name="labor_wage_payments")
    op.drop_index("ix_labor_wage_payments_project_id", table_name="labor_wage_payments")
    op.drop_table("labor_wage_payments")
    op.drop_index("ix_labor_work_entries_work_date", table_name="labor_work_entries")
    op.drop_index("ix_labor_work_entries_worker_id", table_name="labor_work_entries")
    op.drop_index("ix_labor_work_entries_project_id", table_name="labor_work_entries")
    op.drop_table("labor_work_entries")
    op.drop_index("ix_labor_workers_project_id", table_name="labor_workers")
    op.drop_table("labor_workers")
