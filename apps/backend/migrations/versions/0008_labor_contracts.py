from alembic import op
import sqlalchemy as sa


revision = "0008_labor_contracts"
down_revision = "0007_labor_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "labor_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("contract_number", sa.String(40), nullable=False),
        sa.Column("subcontractor_name", sa.String(160), nullable=False),
        sa.Column("scope", sa.String(500), nullable=False),
        sa.Column("pricing_type", sa.String(20), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("contract_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("unit", sa.String(24), nullable=True),
        sa.Column("unit_rate", sa.Numeric(18, 2), nullable=True),
        sa.Column("baseline_document_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="Active"),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["baseline_document_id"], ["project_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_number"),
    )
    op.create_index("ix_labor_contracts_project_id", "labor_contracts", ["project_id"])
    op.create_table(
        "labor_contract_addenda",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("plan_document_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("previous_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("revised_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="Pending approval"),
        sa.Column("submitted_by_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decision_comment", sa.String(500), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contract_id"], ["labor_contracts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_document_id"], ["project_documents.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_labor_contract_addenda_project_id", "labor_contract_addenda", ["project_id"])
    op.create_index("ix_labor_contract_addenda_contract_id", "labor_contract_addenda", ["contract_id"])
    op.create_table(
        "labor_progress_claims",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("claim_number", sa.String(40), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("work_description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="Pending certification"),
        sa.Column("submitted_by_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decision_comment", sa.String(500), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contract_id"], ["labor_contracts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_number"),
    )
    op.create_index("ix_labor_progress_claims_project_id", "labor_progress_claims", ["project_id"])
    op.create_index("ix_labor_progress_claims_contract_id", "labor_progress_claims", ["contract_id"])
    op.create_table(
        "labor_contract_payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("claim_id", sa.Uuid(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("payment_mode", sa.String(24), nullable=False, server_default="Bank transfer"),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("comment", sa.String(500), nullable=True),
        sa.Column("recorded_by_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_id"], ["labor_progress_claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_labor_contract_payments_project_id", "labor_contract_payments", ["project_id"])
    op.create_index("ix_labor_contract_payments_claim_id", "labor_contract_payments", ["claim_id"])
    op.create_index("ix_labor_contract_payments_payment_date", "labor_contract_payments", ["payment_date"])


def downgrade() -> None:
    op.drop_index("ix_labor_contract_payments_payment_date", table_name="labor_contract_payments")
    op.drop_index("ix_labor_contract_payments_claim_id", table_name="labor_contract_payments")
    op.drop_index("ix_labor_contract_payments_project_id", table_name="labor_contract_payments")
    op.drop_table("labor_contract_payments")
    op.drop_index("ix_labor_progress_claims_contract_id", table_name="labor_progress_claims")
    op.drop_index("ix_labor_progress_claims_project_id", table_name="labor_progress_claims")
    op.drop_table("labor_progress_claims")
    op.drop_index("ix_labor_contract_addenda_contract_id", table_name="labor_contract_addenda")
    op.drop_index("ix_labor_contract_addenda_project_id", table_name="labor_contract_addenda")
    op.drop_table("labor_contract_addenda")
    op.drop_index("ix_labor_contracts_project_id", table_name="labor_contracts")
    op.drop_table("labor_contracts")
